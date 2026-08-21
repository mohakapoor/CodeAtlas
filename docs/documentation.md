# CodeAtlas: Architecture & Technical Reference

## 1. Executive Summary
**CodeAtlas** is an agentic engineering assistant designed to ingest, index, and provide a Retrieval-Augmented Generation (RAG) interface across an entire GitHub portfolio. By aggregating multiple repositories (specifically those tagged as `knowledge-base`) into a centralized, structure-aware semantic knowledge base, CodeAtlas delivers accurate answers to complex architectural queries with precise file and line-level citations.

---

## 2. System Architecture

### 2.1 Ingestion & Synchronization
- **Incremental Synchronization**: Integrates with the GitHub API to pull repositories. Uses a local `manifest.json` queue to parse and index only files modified between commits, optimizing ingestion efficiency.
- **Fault Tolerance**: The `manifest.json` serves as a persistent index queue, ensuring at-least-once execution guarantees and seamless recovery in the event of an interruption.

### 2.2 Structure-Aware Parsing
To preserve logical context, CodeAtlas employs specialized parsers rather than generic character-based chunking:
- **Python AST Parser**: Utilizes Python's Abstract Syntax Tree (`ast.parse`) to extract `FunctionDef` and `ClassDef` blocks as cohesive, semantic units.
- **Markdown Parser**: Leverages LangChain's `MarkdownHeaderTextSplitter` to segment documentation based on structural headers.

### 2.3 Embedding & Vector Storage
- **Embedding Model**: Employs `all-MiniLM-L6-v2` via HuggingFace for efficient, private, and localized embeddings.
- **Vector Database**: Utilizes a Qdrant/ChromaDB instance for persistent storage, indexing chunks alongside structured metadata (e.g., repository, filepath, language, symbol).

### 2.4 Interface & Language Model
- **Application Layer**: A Flask-based orchestration server providing a modern, responsive user interface.
- **Generation Engine**: Integrates with LangChain and Google's Gemini models (`gemini-3.1-flash-lite`). The system strictly grounds all generated responses in the retrieved context to mitigate hallucinations.

---

## 3. Retrieval Architecture Evolution

Retrieving context across a diverse codebase requires balancing raw code logic with high-level documentation. Over-indexing on code often deprives the LLM of the explanatory context needed to formulate coherent answers, while over-indexing on documentation omits critical implementation details. 

To achieve the optimal balance, CodeAtlas's retrieval architecture evolved through several structured iterations:

### 3.1 Iteration 1: Static Quota Retrieval (`SplitAndCombineRetriever`)
- **Mechanism**: Executed two isolated vector database queries: one strictly fetching the top 3 Python chunks, and another fetching the top 2 Markdown chunks.
- **Outcome**: Delivered high Answer Relevancy and Faithfulness by guaranteeing plain-English context. However, it suffered from lower overall Recall and Precision due to the inflexible constraints.

### 3.2 Iteration 2: Neural Hybrid Reranking (`HybridRetriever`)
- **Mechanism**: Transitioned to Qdrant's Hybrid Search (combining Dense Vectors with Sparse BM25 scoring) and introduced a HuggingFace Cross-Encoder (`ms-marco-MiniLM-L-6-v2`). It fetched the top 15 chunks of any file type and neural-reranked them to isolate the top 5.
- **Outcome**: Precision and Recall metrics increased significantly. However, Faithfulness and Relevancy declined because the Cross-Encoder frequently prioritized code chunks, starving the LLM of necessary Markdown context.

### 3.3 Iteration 3: Hybrid Split Reranking (`HybridSplitRetriever`)
- **Mechanism**: Attempted to merge the precision of the Cross-Encoder with the diversity of the static quota. It separately fetched and reranked the top 15 Code chunks (keeping the top 3) and the top 15 Documentation chunks (keeping the top 2), then combined them.
- **Outcome**: Achieved the highest Mean Reciprocal Rank (MRR) to date (0.50), but suffered severe regressions in Faithfulness and Correctness. 
- **The Distractor Problem**: The strict requirement to always fetch 3 code chunks forced the inclusion of highly scored exact-keyword code matches, even for pure documentation queries. These mathematically relevant but functionally useless "distractor" chunks confused the generation engine.

### 3.4 Iteration 4: Global Pooling Retrieval (`GlobalRerankRetriever`) (Current Architecture)
To neutralize the distractor problem, CodeAtlas implemented a dynamic, unified reranking strategy:
1. **Candidate Generation**: Executes dual Hybrid Searches against the vector database, fetching the top 15 code candidates and top 15 documentation candidates.
2. **Global Pooling**: Merges candidates from both streams into a unified 30-chunk pool.
3. **Cross-Encoder Reranking**: Evaluates the unified pool holistically using the Cross-Encoder to score each chunk against the user's query.
4. **Dynamic Context Assembly**: Selects the absolute top 5 chunks from the global pool. 

- **Outcome**: This allows for dynamic context allocation—ranging from exclusively code to exclusively documentation—based strictly on semantic relevance. It effectively resolved the distractor problem by pruning irrelevant keyword matches, leading to a dramatic recovery across all Generation metrics.

---

## 4. Evaluation & Metrics

CodeAtlas maintains a rigorous, data-driven evaluation framework to continuously benchmark retrieval and generation performance.

- **Evaluation Dataset**: A curated 52-question dataset (`eval_set.json`) covering symbol lookups, multi-repository logic tracing, and negative queries.
- **Automated Benchmarking**: Utilizes JudgeKit and RAGAS to score the system across standard Information Retrieval and Generation metrics.

**Latest System Metrics:**
- **Retrieval Performance**: Precision: 0.78 | Recall: 0.83
- **Generation Performance**: Faithfulness: 0.88 | Relevance: 0.91 | Correctness: 0.82
