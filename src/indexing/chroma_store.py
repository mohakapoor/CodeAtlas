import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.utils import Chunk

# Load environment variables from .env file
load_dotenv()

# 1. Initialize once globally so we aren't reconnecting on every upsert
_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-2" # User confirmed this model string
)

_vectorstore = Chroma(
    collection_name="code_atlas",
    embedding_function=_embeddings,
    persist_directory="knowledge_base/chroma"
)

def get_vectorstore() -> Chroma:
    """Returns the globally initialized vectorstore."""
    return _vectorstore

def upsert(chunks: list[Chunk]) -> int:
    """
    Upserts Chunk objects into ChromaDB using add_texts for minimal overhead.
    Returns the number of chunks successfully indexed.
    """
    if not chunks:
        return 0
        
    texts = [c.content for c in chunks]
    metadatas = [c.metadata for c in chunks]
    ids = [c.id for c in chunks]
    
    try:
        _vectorstore.add_texts(
            texts=texts,
            metadatas=metadatas,
            ids=ids
        )
        return len(ids)
    except Exception as e:
        print(f"Error upserting chunks into ChromaDB: {e}")
        return 0

def delete_file(repo: str, path: str) -> None:
    """
    Deletes all chunks associated with a specific file from a repo.
    Hooks directly into the underlying Chroma collection to delete by metadata.
    """
    try:
        _vectorstore.delete(
            where={
                "$and": [
                    {"repo": repo},
                    {"path": path}
                ]
            }
        )
    except Exception as e:
        print(f"Error deleting file {path} from ChromaDB: {e}")

def similarity_search(
    query: str,
    k: int = 5,
    filter: dict | None = None,
):
    """
    Basic retriever entry point with metadata filtering support.
    """
    return _vectorstore.similarity_search(
        query,
        k=k,
        filter=filter,
    )
