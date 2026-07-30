import os
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from langchain_huggingface import HuggingFaceEmbeddings
from src.utils import Chunk
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Load environment variables from .env file
load_dotenv()

# 1. Initialize once globally so we aren't reconnecting on every upsert
_dense_embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# 2. FastEmbed generates our BM25-like sparse vectors but understands syntax!
_sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")

# 3. Initialize the Qdrant Client (saving to local folder)
_client = QdrantClient(path="knowledge_base/qdrant")

# 4. Ensure the collection exists before creating the VectorStore
if not _client.collection_exists("code_atlas"):
    _client.create_collection(
        collection_name="code_atlas",
        vectors_config=models.VectorParams(
            size=384,  # all-MiniLM-L6-v2 output dimension
            distance=models.Distance.COSINE
        ),
        sparse_vectors_config={
            "langchain-sparse": models.SparseVectorParams() # Default sparse vector name for langchain
        }
    )

_vectorstore = QdrantVectorStore(
    client=_client,
    collection_name="code_atlas",
    embedding=_dense_embeddings,
    sparse_embedding=_sparse_embeddings,
    retrieval_mode=RetrievalMode.HYBRID
)

def get_vectorstore() -> QdrantVectorStore:
    """Returns the globally initialized vectorstore."""
    return _vectorstore

def upsert(chunks: list[Chunk]) -> int:
    """
    Upserts Chunk objects into Qdrant.
    It automatically generates dense AND sparse vectors in the background!
    """
    if not chunks:
        return 0
        
    import uuid
    
    texts = [c.content for c in chunks]
    metadatas = [c.metadata for c in chunks]
    
    # Convert custom string IDs into valid Qdrant UUIDs deterministically
    ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, c.id)) for c in chunks]
    
    try:
        _vectorstore.add_texts(
            texts=texts,
            metadatas=metadatas,
            ids=ids
        )
        return len(ids)
    except Exception as e:
        print(f"Error upserting chunks into Qdrant: {e}")
        return 0

def delete_file(repo: str, path: str) -> None:
    """
    Deletes all chunks associated with a specific file from a repo.
    """
    try:
        _client.delete(
            collection_name="code_atlas",
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(key="metadata.repo", match=models.MatchValue(value=repo)),
                        models.FieldCondition(key="metadata.path", match=models.MatchValue(value=path)),
                    ]
                )
            )
        )
    except Exception as e:
        print(f"Error deleting file {path} from Qdrant: {e}")
