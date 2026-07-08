import os
import dotenv
from pathlib import Path
from src.indexing.chroma_store import get_vectorstore
from src.retrieval.retrievers import SplitAndCombineRetriever
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

def run_interactive_rag():
    dotenv.load_dotenv()
    
    print("Initializing Split & Combine Retriever...")
    # Fetch 3 code chunks and 2 documentation chunks
    base_retriever = SplitAndCombineRetriever(code_k=3, doc_k=2)
    
    # Wrap it in a RunnableLambda to make it compatible with LangChain LCEL
    from langchain_core.runnables import RunnableLambda
    retriever = RunnableLambda(lambda q: base_retriever.retrieve(q))
    
    print("Loading LLM (gemini-2.5-flash)...")
    llm = init_chat_model(
        model="gemini-2.5-flash",
        model_provider="google_genai",
        temperature=0.2,
        streaming=False,
    )
    
    prompt = ChatPromptTemplate.from_template(
        """
        You are an expert programming assistant reading a codebase.
        Answer the question based only on the following context.
        
        {context}

        Question: {question}

        Answer:

        Answer in a bit of detail. If you don't know the answer, just say "I don't know".
        """
    )
    
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
        
    rag_chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    
    print("\n" + "="*40)
    print(" CodeAtlas RAG System Ready!")
    print("="*40)
    print("Type 'exit' or 'quit' to stop.\n")
    
    while True:
        try:
            query = input("Ask a question about your codebase: ")
            if query.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            
            if not query.strip():
                continue
                
            print("\nThinking...")
            answer = rag_chain.invoke(query)
            
            print("\n" + "-"*40)
            print("Answer:")
            print(answer)
            print("-"*40)
            
            # Fetch docs manually to show sources
            print("Sources:")
            docs = base_retriever.retrieve(query)
            for doc in docs:
                repo = doc.metadata.get('repo', 'Unknown repo')
                path = doc.metadata.get('path', 'Unknown file')
                chunk_type = doc.metadata.get('type', 'chunk')
                print(f"  - [{repo}] {path} ({chunk_type})")
            print("\n")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n[!] Error: {e}")

if __name__ == "__main__":
    run_interactive_rag()
