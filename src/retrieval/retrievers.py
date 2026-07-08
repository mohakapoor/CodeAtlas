from abc import ABC, abstractmethod
from src.indexing.chroma_store import get_vectorstore

class BaseRetriever(ABC):
    """
    Abstract base class for all retrievers.
    """
    def __init__(self):
        self.vectorstore = get_vectorstore()

    @abstractmethod
    def retrieve(self, query: str, k: int = 5):
        pass

class VectorRetriever(BaseRetriever):
    """
    A simple baseline retriever that performs a standard vector similarity search.
    """
    def retrieve(self, query: str, k: int = 5):
        return self.vectorstore.similarity_search(query, k=k)

class MMRRetriever(BaseRetriever):
    """
    A retriever that uses Maximal Marginal Relevance (MMR) to optimize for both 
    relevance and diversity.
    """
    def __init__(self, fetch_k: int = 20, lambda_mult: float = 0.5):
        super().__init__()
        self.fetch_k = fetch_k
        self.lambda_mult = lambda_mult

    def retrieve(self, query: str, k: int = 5):
        return self.vectorstore.max_marginal_relevance_search(
            query, 
            k=k, 
            fetch_k=self.fetch_k, 
            lambda_mult=self.lambda_mult
        )

class CodeOnlyRetriever(BaseRetriever):
    """
    A retriever that uses metadata filtering to strictly exclude markdown and text files,
    ensuring that only actual source code is retrieved.
    """
    def retrieve(self, query: str, k: int = 5):
        return self.vectorstore.similarity_search(
            query, 
            k=k, 
            filter={"language": {"$nin": ["markdown", "text"]}}
        )

class SplitAndCombineRetriever(BaseRetriever):
    """
    Executes two separate searches to guarantee a balanced context window:
    one strict code search, and one strict documentation search.
    """
    def __init__(self, code_k: int = 3, doc_k: int = 2):
        super().__init__()
        self.code_k = code_k
        self.doc_k = doc_k

    def retrieve(self, query: str, k: int = 5):
        # The 'k' argument here is ignored since we use the pre-configured code_k and doc_k,
        # but we keep it in the signature to match the BaseRetriever interface.
        
        code_results = self.vectorstore.similarity_search(
            query, 
            k=self.code_k, 
            filter={"language": {"$nin": ["markdown", "text"]}}
        )
        
        doc_results = self.vectorstore.similarity_search(
            query, 
            k=self.doc_k, 
            filter={"language": {"$in": ["markdown", "text"]}}
        )
        
        return code_results + doc_results
