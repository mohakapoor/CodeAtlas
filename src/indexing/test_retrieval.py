from pathlib import Path
from src.indexing.chroma_store import get_vectorstore, upsert
from src.parsing.pyparser import parse_py
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


def test_retrieval():
    # 1. Parse our local test.py file and upsert it into the DB for testing
    print("Parsing src/parsing/test.py...")
    chunks = parse_py(Path("src/parsing/test.py"), repo="test_repo")
    
    if chunks:
        indexed_count = upsert(chunks)
        print(f"Upserted {indexed_count} chunks from test.py into ChromaDB.")
    else:
        print("Warning: No chunks generated from test.py.")

    # 2. Fetch our vector store
    vector_store = get_vectorstore()
    
    # Create a retriever that fetches the top 5 most relevant chunks
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    
    # 3. Initialize the LLM
    llm = init_chat_model(
        model="gemini-2.5-flash",
        model_provider="google_genai",
        temperature=0.2,
        streaming=False,
    )
    
    # 4. Create an LCEL prompt template for RAG
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
        
    # 5. Construct the LCEL chain
    rag_chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    
    # 6. Interactive loop
    print("\nRAG System Ready! Type 'exit' or 'quit' to stop.")
    while True:
        try:
            query = input("\nAsk a question about your code: ")
            if query.lower() in ["exit", "quit"]:
                break
                
            print("Thinking...")
            # Note: with LCEL we pass the query string directly, not a dict with 'input'
            answer = rag_chain.invoke(query)
            
            print("\n=== Answer ===")
            print(answer)
            print("\n=== Sources ===")
            
            # Since the LCEL chain only outputs the final string, we fetch docs manually to show sources
            docs = retriever.invoke(query)
            for doc in docs:
                print(f"- {doc.metadata.get('path', 'Unknown file')} (Chunk {doc.metadata.get('chunk_idx', '?')})")
                
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    test_retrieval()
