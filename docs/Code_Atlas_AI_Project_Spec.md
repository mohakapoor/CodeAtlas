# GitGraph AI — Project Spec (Updated)

**One-liner:** An agentic engineering assistant that indexes an entire GitHub portfolio (not just one repo) and answers natural-language questions about your own code history, with citations back to file/line.

**Not this:** Another "chat with your PDFs" RAG demo.

**Timeline:** 2 weeks, ~5 hrs/day focused work (~70 hrs total), AI-assisted.

**Structure:** Two stages — MVP (Week 1) → Full version (Week 2). Only add to resume/site once a stage is demo-clean and eval numbers are captured.

---

## Stage 1: MVP (Week 1, ~30 hrs)

### Scope
- Ingest 10–15 of your own repos via GitHub API (topic-filtered)
- Parsers: `.py` (AST → functions/classes) + `.md` only
- Chroma + BGE-M3 embeddings; metadata stored separately from embedded content
- Retrieval: single-shot (question → vector search → LLM answer with citation) — **no** planner/agent yet
- Minimal FastAPI backend + basic chat UI

### Metadata schema (per chunk)
`repository`, `file_path`, `language`, `start_line`, `end_line`, `function/class_name`, `repository_topics`

### Eval set (build in parallel with the app, not after)
- Hand-write 25–30 Q&A pairs with known ground truth, e.g.:
  - "Which repo has JWT auth?" → IDS repo, `auth.py`
  - "Which repos use FastAPI?" → [list]
- This is what makes your metrics real instead of vibes — build it as you build parsing, not at the end.

### MVP metrics to capture
- Repos indexed / files parsed / chunks generated (e.g. "15 repos, 40K+ LOC, 1,100 chunks")
- **Retrieval accuracy**: % of eval questions where correct file/repo appears in top-3 retrieved chunks (headline number — report honestly even if it's ~70%, improve in Stage 2)
- Average query latency (embedding + retrieval + LLM response)

---

## Stage 2: Full Version (Week 2, ~35–40 hrs)

### Scope additions
- **Notebook (`.ipynb`) handling**: convert via `nbconvert`/`jupytext` to `.py`, keeping markdown cells inline as `# %% [markdown]` comments (not split into a separate file). Add a self-referential cell marker before each cell's code:
  `# --- Cell N (lines X-Y): one-line description ---`
  - Mirror this in a companion `.md` file (cell number, line range, description) — generate both from the **same conversion pass** so line numbers stay in sync by construction.
  - AST parser splits on these `# --- Cell N ---` markers directly.
  - The `.md` file doubles as an embeddable table-of-contents for fast "which cell does X" lookups.
  - Capture cell **outputs** (stream/execute_result — accuracy numbers, printed metrics, tracebacks), not just markdown/code — this is where questions like "what accuracy did I get" actually get answered from.
- Additional parsers: `Dockerfile` (whole file), `docker-compose.yml` (services), GitHub Actions YAML (workflow level)
- Retrieval upgrade: LangGraph graph — `Planner → Retriever → (optional) File Reader tool → LLM → Answer`
  - File Reader tool opens the original file via stored metadata when retrieved chunks aren't sufficient context
- Line-level citations in every answer
- Public deployment — becomes "portfolio mode" for recruiters to query live
- **Stretch only if time remains**: incremental re-indexing via GitHub Action on push (detect changed files → rebuild only those embeddings)

### Full-version metrics
- Re-run the *same* eval set, expand to ~50 questions
- Retrieval accuracy improvement vs MVP (e.g. "71% → 90% top-3 accuracy after AST-aware chunking + file-reader fallback")
- Latency at scale
- Coverage: file types / repos / total chunks indexed
- Optional if publicly deployed: uptime / query volume

---

## Explicitly out of scope for both stages
- GraphRAG/Neo4j (add later only if relationship traversal proves necessary)
- Duplicate code detection, dependency/CVE scanning, architecture-evolution summaries — v3 roadmap, not MVP or full version
- Supporting arbitrary GitHub usernames at scale (rate limits, private repo auth, monorepos) — build against your own repos first; generalize only after retrieval is proven

## Tech stack
Python, FastAPI, LangGraph, ChromaDB, BGE-M3, GitHub API, Git, React/Next.js frontend

## Resume bullet target (fill in real numbers once measured)
"Built an agentic RAG system indexing 15+ repositories (1,200+ AST-parsed code chunks across 5 file types); achieved [X]% top-3 retrieval accuracy on a 50-question hand-labeled eval set using LangGraph orchestration and BGE-M3 embeddings, with sub-2s average query latency."

## Ground rule
Don't add this to resume/LinkedIn/portfolio until a stage is demo-clean and you've personally verified the eval questions return correct, cited answers. Keep applying with the current resume in the meantime — don't gate applications on this build.
