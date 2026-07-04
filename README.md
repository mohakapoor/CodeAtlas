# Code Atlas

**Code Atlas** is an agentic engineering assistant designed to index your entire GitHub portfolio and answer natural-language questions about your codebase, complete with file and line-level citations.

## The Basic Idea

Unlike typical "chat with your codebase" tools that focus on a single repository, Code Atlas is built to ingest and understand a portfolio of repositories at once. It automatically pulls your public repositories (specifically those tagged as a `knowledge-base`), parses the source code (starting with Python AST and Markdown), and indexes them into a vector database.

When you ask a natural-language question (e.g., "Which repo uses FastAPI?"), the system searches the index to retrieve the relevant code chunks and generates an answer that explicitly cites the source repository, file, and line numbers.

## Workflow

1. **Clone**: Fetch public repositories via the GitHub API that match the target topic (`knowledge-base`).
2. **Parse**: Extract and logically chunk the source code and documentation.
3. **Index**: Embed the chunks and store them in ChromaDB for fast, context-aware retrieval.
