<div align="center">

# Code Atlas
**Intelligent Codebase RAG & Agentic Engineering Assistant**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-Framework-black?style=for-the-badge&logo=langchain&logoColor=white)](https://python.langchain.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20Store-EF3959?style=for-the-badge&logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-LLM-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)](https://deepmind.google/technologies/gemini/)

[**Documentation**](docs/documentation.md) • [**GitHub Repo**](https://github.com/mohakapoor/CodeAtlas)

</div>

---

**Code Atlas** is an agentic engineering assistant designed to index your entire GitHub portfolio and answer natural-language questions about your codebase, complete with file and line-level citations.

## The Basic Idea

Unlike typical "chat with your codebase" tools that focus on a single repository, Code Atlas is built to ingest and understand a portfolio of repositories at once. It automatically pulls your public repositories (specifically those tagged as a `knowledge-base`), parses the source code (starting with Python AST and Markdown), and indexes them into a vector database.

When you ask a natural-language question (e.g., "Which repo uses FastAPI?"), the system searches the index to retrieve the relevant code chunks and generates an answer that explicitly cites the source repository, file, and line numbers.

## Features & Architecture

Code Atlas is designed to be highly resilient, efficient, and offline-friendly for indexing.

- **Local Embeddings**: Embeddings are generated using a local HuggingFace model (`all-MiniLM-L6-v2`). This avoids rate limits and API costs during large ingestion runs, making the indexing process completely local and free.
- **Robust Incremental Syncing**: Instead of relying purely on GitHub commit SHAs, Code Atlas maintains a file-by-file `index_queue` inside a local `manifest.json`. If indexing crashes midway, the next run will pick up exactly where it left off, giving you at-least-once execution guarantees.
- **Rigorous Evaluation Suite**: Included is a domain-specific evaluation framework that calculates Hit Rate and MRR against a strict 52-question dataset spanning symbol lookups, multi-repo logic, configuration queries, and negative queries.
- **AST Parsing**: Smart chunking utilizing Python's AST to extract meaning natively, rather than blind string splitting.

## Workflow

1. **Clone/Sync**: Fetch public repositories via the GitHub API that match the target topic (e.g. `knowledge-base`). Uses `git pull` for incremental updates.
2. **Parse**: Extract and logically chunk the source code and documentation.
3. **Index**: Embed the chunks and store them in ChromaDB for fast, context-aware retrieval.
4. **Chat**: Run RAG pipelines across the whole database to answer arbitrary technical questions.

## Getting Started

Make sure you have [uv](https://github.com/astral-sh/uv) installed, then install dependencies:

```bash
uv sync
```

### 1. Ingest Repositories

Configure your target GitHub username and topic via environment variables (default is `mohakapoor` and `knowledge-base`):

```bash
uv run python -m src.ingest
```

This will clone the repositories, download the local embedding weights, and build your ChromaDB index inside `knowledge_base/chroma`.

### 2. Chat with Code Atlas

Test the RAG retrieval and question answering:

```bash
uv run python -m src.test_rag
```

### 3. Evaluate System

Code Atlas includes a rigorous evaluation suite for both retrieval and generation capabilities.

**Latest Statistics:**
- **Retrieval**: Precision: 0.78, Recall: 0.83
- **Generation**: Faithfulness: 0.88, Relevance: 0.91, Correctness: 0.82

Run the retrieval evaluation suite on the curated dataset:

```bash
uv run python -m src.eval.eval_retrieval
```
