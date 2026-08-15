# CodeAtlas: Comprehensive Architecture & Documentation

## 1. Project Goal & Vision
**CodeAtlas** is an agentic engineering assistant designed to ingest, index, and provide a conversational interface (RAG) over an entire GitHub portfolio. 

Unlike typical tools that chat with a single repository, CodeAtlas aggregates multiple public repositories (specifically those tagged as `knowledge-base`) into a centralized, structure-aware semantic knowledge base. The goal is to provide accurate, hallucination-free answers to complex architectural questions, complete with precise file and line-level citations.

---

## 2. Core Architecture

### A. Ingestion & Synchronization
- **Incremental Sync**: The system pulls repositories from GitHub. Instead of re-indexing everything, it uses Git diffs and a local `manifest.json` queue to only parse and index files that have actually changed between commits.
- **Resilience**: If the indexing process crashes, the `manifest.json` acts as an `index_queue`, guaranteeing at-least-once execution upon restart.

### B. Structure-Aware Parsing
Naive character chunking destroys code logic. CodeAtlas solves this via specialized parsers:
- **Python AST Parser**: Uses `ast.parse` to extract `FunctionDef` and `ClassDef` directly, treating them as atomic semantic chunks. 
- **Markdown Parser**: Uses LangChain's `MarkdownHeaderTextSplitter` to intelligently chunk documentation by headers rather than arbitrary lengths.

### C. Embedding & Storage
- **Local Privacy**: Uses `all-MiniLM-L6-v2` via HuggingFace for fast, free, and private local embeddings.
- **Vector Database**: Uses a local Qdrant/ChromaDB instance to store vector representations of the codebase, tagged with rich metadata (`repo`, `path`, `language`, `symbol`).

### D. Chat & Interface
- **Orchestrator**: A Flask application serves as the frontend, utilizing a sleek `#0f1115` UI with glass-like gradients.
- **LLM Engine**: Powered by LangChain and Google's Gemini models (`gemini-3.1-flash-lite`). It strictly grounds answers in the retrieved context to prevent hallucination.

---

## 3. The Retrieval Evolution (Iterative Development)

Retrieval is the hardest part of a Code RAG system. If you only retrieve code, the LLM doesn't know *why* something exists. If you only retrieve READMEs, the LLM doesn't know *how* it's implemented. 

CodeAtlas has iterated through three major retrieval architectures to solve this:

### Iteration 1: `SplitAndCombineRetriever`
- **How it worked**: Forced a strict quota. It searched the vector database twice: once to get the top 3 Python chunks, and once to get the top 2 Markdown chunks.
- **Results**: High Faithfulness and Answer Relevancy (because the LLM always had plain-English documentation to read), but low overall Recall and Precision.

### Iteration 2: `HybridRetriever`
- **How it worked**: Switched to Qdrant's native Hybrid Search (Dense + Sparse BM25) and added a HuggingFace **Cross-Encoder** (`ms-marco-MiniLM-L-6-v2`) for neural reranking. It fetched the top 15 chunks of *any type* and reranked them to get the absolute top 5.
- **Results**: Precision and Recall skyrocketed. However, **Faithfulness and Relevancy dropped**. 
- **The Problem**: The Cross-Encoder often decided that 5 code chunks were mathematically the most relevant, starving the LLM of the Markdown context it needed to generate human-readable explanations. 

### Iteration 3: `HybridSplitRetriever` (Current Architecture)
- **How it works**: Combines the mathematical superiority of the Cross-Encoder with the forced diversity of the Split-and-Combine method.
- **The Logic**: 
  1. Grabs the top 15 Code chunks (via Hybrid Search), reranks them with the Cross-Encoder, and strictly keeps the top 3.
  2. Grabs the top 15 Doc chunks (via Hybrid Search), reranks them with the Cross-Encoder, and strictly keeps the top 2.
  3. Combines them into a perfect 5-chunk context window.
- **The Unexpected Results**: While MRR (Mean Reciprocal Rank) jumped to its highest ever (0.50), **Faithfulness and Correctness crashed** (down to 0.81 and 0.72).
- **The Distractor Problem (Why V3 Failed)**: Because the retriever uses highly powerful exact keyword matching (BM25) and is *forced* to find 3 code chunks on every query, it finds highly convincing "distractor" code chunks even for pure documentation questions. The LLM gets confused by these highly-scored but functionally irrelevant exact-keyword matches, causing hallucinations.

### The Path Forward (Solving the Distractor Problem)
To fix the rigid 3/2 split causing distractors, three solutions are currently under consideration:
1. **Cross-Encoder Score Thresholding**: Keep the split, but drop any chunks that score below a certain threshold (e.g., `0.3`), naturally pruning bad code distractors before they reach the LLM.
2. **The 30-Chunk Global Rerank**: Fetch 15 Code and 15 Doc chunks, pool them together, run the Cross-Encoder on all 30, and take the global Top 5. This allows a dynamic allocation (e.g., 5 docs, 0 code) depending on the query.
3. **Agentic LLM Router**: Place a fast LLM (like Gemini Flash) in front of the vector database to intercept the user's query and dynamically output the exact `code_k` and `doc_k` needed.

---

## 4. Evaluation System
CodeAtlas does not rely on "vibes" for testing. It uses a rigorous, data-driven evaluation suite:
- **Custom Dataset**: A 52-question `eval_set.json` featuring symbol lookups, multi-repo logic traces, and negative queries.
- **JudgeKit / RAGAS**: Automated evaluation of the `HybridSplitRetriever`'s output, scoring the pipeline on Information Retrieval metrics (Hit Rate @ K, MRR, Precision, Recall) and LLM Generation metrics (Faithfulness, Answer Relevancy, Correctness).
