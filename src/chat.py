import dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from src.retrieval.retrievers import GlobalRerankRetriever

class ChatSession:
    """Manages conversational memory with a strict limit."""
    def __init__(self, max_history=10):
        self.history = []
        self.max_history = max_history

    def add_user(self, message: str):
        self.history.append({"role": "user", "content": message})
        self._trim()

    def add_assistant(self, message: str):
        self.history.append({"role": "assistant", "content": message})
        self._trim()

    def _trim(self):
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def clear(self):
        self.history = []

class PromptBuilder:
    """Constructs the final LLM prompt as a list of structured messages."""
    @staticmethod
    def build(query: str, history: list, context_docs: list) -> list[BaseMessage]:
        parts = [
            "You are CodeAtlas, an expert programming assistant.\n",
            "INSTRUCTIONS:",
            "- Answer the user's question based ONLY on the following codebase context.",
            "- Assume the user is the owner/developer of this codebase. If they say 'my code', 'our project', or 'do I have', they are referring to the codebase context provided below.",
            "- If the answer cannot be determined from the retrieved context, explicitly state that the information is unavailable.",
            "- Do not invent functions, files, repositories or implementation details.",
            "- When possible, mention the file where the information came from.\n",
            "RETRIEVED CONTEXT:\n"
        ]
        
        # Format Context with Metadata and Numbering
        for i, doc in enumerate(context_docs, 1):
            repo = doc.metadata.get("repo", "Unknown")
            path = doc.metadata.get("path", "Unknown")
            symbol = doc.metadata.get("symbol", "")
            start_line = doc.metadata.get("start_line", "")
            end_line = doc.metadata.get("end_line", "")
            
            parts.append(f"Context {i}")
            parts.append(f"Repository: {repo}")
            parts.append(f"File: {path}")
            if symbol:
                parts.append(f"Symbol: {symbol}")
            if start_line and end_line:
                parts.append(f"Lines: {start_line}-{end_line}")
                
            parts.append(f"<chunk>\n{doc.page_content}\n</chunk>")
            parts.append("-" * 20)
            
        system_prompt = "\n".join(parts)
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]
        
        # Append Conversation History as actual Message objects
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
                
        # Append Current Question
        messages.append(HumanMessage(content=query))
        
        return messages

class CodeAtlasChat:
    """
    Orchestrator that handles the MVP RAG pipeline.
    """
    def __init__(self, model_name="gemini-3.1-flash-lite"):
        dotenv.load_dotenv()
        
        self.llm = init_chat_model(
            model=model_name,
            model_provider="google_genai",
            temperature=0.2,
            streaming=False,
        )
        self.retriever = GlobalRerankRetriever()
        self.session = ChatSession(max_history=10)

    def ask(self, query: str) -> dict:
        """
        Executes a single turn of the pipeline.
        query -> retrieve -> build prompt -> generate -> update history
        """
        # Retrieve using ONLY the Current Question
        docs = self.retriever.retrieve(query)
        
        # check if no docs are found
        if not docs:
            return {
                "answer": "I couldn't find any relevant code or documentation for that query.",
                "sources": []
            }
            
        # Format sources for the frontend (Deduplicated)
        sources = []
        seen = set()
        
        for doc in docs:
            repo = doc.metadata.get("repo", "Unknown")
            path = doc.metadata.get("path", "Unknown")
            symbol = doc.metadata.get("symbol", "")
            chunk_type = doc.metadata.get("type", "chunk")
            
            key = (repo, path, symbol)
            if key in seen:
                continue
                
            seen.add(key)
            sources.append({
                "repo": repo,
                "path": path,
                "type": chunk_type,
                "symbol": symbol
            })

        messages = PromptBuilder.build(query, self.session.history, docs)
        
        ai_msg = self.llm.invoke(messages)
        answer = ai_msg.content
        

        self.session.add_user(query)
        self.session.add_assistant(answer)
        
        return {"answer": answer, "response": answer, "sources": sources}
