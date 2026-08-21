from abc import ABC, abstractmethod
from src.indexing.qdrant_store import get_vectorstore
from qdrant_client.http import models

class BaseRetriever(ABC):
    def __init__(self):
        self.vectorstore = get_vectorstore()

    @abstractmethod
    def retrieve(self, query: str, k: int = 5):
        pass

class VectorRetriever(BaseRetriever):
    def retrieve(self, query: str, k: int = 5):
        return self.vectorstore.similarity_search(query, k=k)

class CodeOnlyRetriever(BaseRetriever):
    def retrieve(self, query: str, k: int = 5):
        # Qdrant typed filter syntax
        qdrant_filter = models.Filter(
            must_not=[
                models.FieldCondition(
                    key="metadata.language",
                    match=models.MatchAny(any=["markdown", "text"])
                )
            ]
        )
        return self.vectorstore.similarity_search(
            query, 
            k=k, 
            filter=qdrant_filter
        )

class SplitAndCombineRetriever(BaseRetriever):
    def __init__(self, code_k: int = 3, doc_k: int = 2):
        super().__init__()
        self.code_k = code_k
        self.doc_k = doc_k

    def retrieve(self, query: str, k: int = 5):
        code_filter = models.Filter(
            must_not=[
                models.FieldCondition(
                    key="metadata.language",
                    match=models.MatchAny(any=["markdown", "text"])
                )
            ]
        )
        doc_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.language",
                    match=models.MatchAny(any=["markdown", "text"])
                )
            ]
        )
        
        code_results = self.vectorstore.similarity_search(query, k=self.code_k, filter=code_filter)
        doc_results = self.vectorstore.similarity_search(query, k=self.doc_k, filter=doc_filter)
        
        return code_results + doc_results

class HybridRetriever(BaseRetriever):
    def __init__(self):
        super().__init__()
        from sentence_transformers import CrossEncoder
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.base_retriever = self.vectorstore.as_retriever(search_kwargs={"k": 15})

    def retrieve(self, query: str, k: int = 5):
        # Fetch initial top K*3 docs from Qdrant Hybrid Search
        self.base_retriever.search_kwargs["k"] = max(15, k * 3)
        docs = self.base_retriever.invoke(query)
        
        if not docs:
            return []
            
        # Neural Reranking
        pairs = [[query, doc.page_content] for doc in docs]
        scores = self.cross_encoder.predict(pairs)
        
        scored_docs = list(zip(scores, docs))
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Return the absolute top k
        return [doc for score, doc in scored_docs[:k]]

class HybridSplitRetriever(BaseRetriever):
    def __init__(self, code_k: int = 3, doc_k: int = 2):
        super().__init__()
        from sentence_transformers import CrossEncoder
        
        self.code_k = code_k
        self.doc_k = doc_k
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.base_retriever = self.vectorstore.as_retriever()

    def retrieve(self, query: str, k: int = 5):
        from qdrant_client.http import models
        
        results = []
        
        # Code Retrieval
        if self.code_k > 0:
            code_filter = models.Filter(
                must_not=[
                    models.FieldCondition(
                        key="metadata.language",
                        match=models.MatchAny(any=["markdown", "text"])
                    )
                ]
            )
            code_docs = self.vectorstore.similarity_search(query, k=15, filter=code_filter)
            
            if code_docs:
                pairs = [[query, doc.page_content] for doc in code_docs]
                scores = self.cross_encoder.predict(pairs)
                scored = list(zip(scores, code_docs))
                scored.sort(key=lambda x: x[0], reverse=True)
                results.extend([doc for score, doc in scored[:self.code_k]])
                
        # Doc Retrieval
        if self.doc_k > 0:
            doc_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.language",
                        match=models.MatchAny(any=["markdown", "text"])
                    )
                ]
            )
            doc_docs = self.vectorstore.similarity_search(query, k=15, filter=doc_filter)
            
            if doc_docs:
                pairs = [[query, doc.page_content] for doc in doc_docs]
                scores = self.cross_encoder.predict(pairs)
                scored = list(zip(scores, doc_docs))
                scored.sort(key=lambda x: x[0], reverse=True)
                results.extend([doc for score, doc in scored[:self.doc_k]])
                
        return results


class GlobalRerankRetriever(BaseRetriever):

    def __init__(self):
        super().__init__()
        from sentence_transformers import CrossEncoder
        
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.base_retriever = self.vectorstore.as_retriever()

    def retrieve(self, query: str, k: int = 5):
        from qdrant_client.http import models
        
        #Fetch Code Candidates
        code_filter = models.Filter(
            must_not=[
                models.FieldCondition(
                    key="metadata.language",
                    match=models.MatchAny(any=["markdown", "text"])
                )
            ]
        )
        code_candidates = self.vectorstore.similarity_search(query, k=15, filter=code_filter)
        
        #Fetch Doc Candidates
        doc_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.language",
                    match=models.MatchAny(any=["markdown", "text"])
                )
            ]
        )
        doc_candidates = self.vectorstore.similarity_search(query, k=15, filter=doc_filter)
        combined_pool = code_candidates + doc_candidates 
        if not combined_pool:
            return []
        pairs = [[query, doc.page_content] for doc in combined_pool]
        scores = self.cross_encoder.predict(pairs)
        
        #Global Sort & Slice
        scored = list(zip(scores, combined_pool))
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [doc for score, doc in scored[:k]]
