import os
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from langchain_huggingface import HuggingFaceEmbeddings
from src.utils import Chunk
from qdrant_client import QdrantClient
from qdrant_client.http import models


load_dotenv()
_dense_embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)
_sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")
_client = QdrantClient(path="knowledge_base/qdrant")



if not _client.collection_exists("code_atlas"):
    _client.create_collection(
        collection_name="code_atlas",
        vectors_config=models.VectorParams(
            size=384,
            distance=models.Distance.COSINE
        ),
        sparse_vectors_config={
            "langchain-sparse": models.SparseVectorParams()
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
    return _vectorstore

def upsert(chunks: list[Chunk]) -> int:
    if not chunks:
        return 0
        
    import uuid
    texts = [c.content for c in chunks]
    metadatas = [c.metadata for c in chunks]
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
