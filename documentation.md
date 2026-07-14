# CodeAtlas: Intelligent Codebase RAG & Semantic Search

## 1. Project Vision
CodeAtlas aims to be a next-generation codebase understanding and Semantic Search tool. Traditional vector searches often fail on codebases because they use naive character chunking, which breaks code logic in half, and they suffer from "README domination," where dense markdown documentation crowds out actual source code in search results. 

CodeAtlas solves this by applying **structure-aware parsing** (e.g., AST-based extraction for Python) and **segmented metadata retrieval**, creating a semantic knowledge base. The ultimate goal is to provide an AI assistant that can accurately trace logic, find components, and answer highly specific architectural questions across multiple repositories simultaneously without hallucinating or losing context.

---

## 2. Current State
CodeAtlas is currently a fully functional local RAG (Retrieval-Augmented Generation) system. It successfully:
- Clones and syncs target repositories from GitHub.
- Parses Python, Markdown, and Text files into structurally logical chunks.
- Embeds and stores these chunks in a local ChromaDB instance with rich metadata.
- Evaluates retrieval performance across a custom dataset, achieving a highly accurate baseline (~78% Hit Rate on pure code logic).
- Provides an interactive terminal RAG interface (powered by Gemini) to query the synced repositories.

---

## 3. Architecture & Core Components

### A. Data Ingestion Layer
- **`src/github/sync_github.py`**: Manages cloning and pulling updates for target repositories into a local `knowledge_base/repos/` directory.
- **`src/ingest.py`**: The orchestration script that traverses the synced repositories and passes files to the appropriate parsers.

### B. Parsing Layer (Structure-Aware Chunking)
CodeAtlas respects file types rather than blindly chunking by character count:
- **`src/parsing/pyparser.py`**: Uses Python's built-in AST (Abstract Syntax Tree) to extract complete functions and classes along with their docstrings. This ensures the LLM receives unbroken logical units of code.
- **`src/parsing/mdparser.py`**: Splits Markdown files logically by `H1` and `H2` headers.
- **`src/parsing/textparser.py`**: Handles generic text fallback using standard recursive character splitting.

### C. Indexing & Storage Layer
- **`src/indexing/chroma_store.py`**: Manages the initialization and connection to the persistent local ChromaDB vector store.
- **`src/indexing/indexer.py`**: Takes the parsed chunks, generates embeddings, and inserts them into ChromaDB alongside heavily structured metadata (e.g., `repo`, `filename`, `language`, `type`).

### D. Retrieval Layer (The "Split & Combine" Strategy)
- **`src/retrieval/retrievers.py`**: Contains the retrieval logic. A major architectural breakthrough in CodeAtlas is solving the "README domination" problem. Instead of using blunt mathematical penalties like MMR (Maximal Marginal Relevance), CodeAtlas implements a **`SplitAndCombineRetriever`**. 
  - It executes two parallel vector searches using metadata filtering:
    1. **Code Retrieval:** Fetches the top 3 source code chunks (strictly excluding `.md`/`.txt`).
    2. **Documentation Retrieval:** Fetches the top 2 documentation chunks.
  - It merges them to guarantee the LLM receives a perfectly balanced context window (raw logic + high-level docs).

### E. Evaluation & Testing Layer
- **`src/eval/eval_set.json`**: A rigorous, structured dataset of queries mapped to their expected files (or lists of repositories) across the codebase.
- **`src/eval/eval_retrieval.py`**: A custom evaluation suite that scores the system using **Hit Rate @ 5** (did it find the file?) and **MRR @ 5** (how fast did it find the file?), allowing for data-driven iteration on the retrieval strategy.

### F. Generation / RAG Layer
- **`src/test_rag.py`**: The interactive LangChain pipeline. It takes user queries, passes them through the `SplitAndCombineRetriever`, formats the injected context, and prompts Gemini to provide a detailed, accurate answer along with explicit source citations.
