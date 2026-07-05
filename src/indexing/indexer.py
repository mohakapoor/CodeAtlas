from pathlib import Path
from src.parsing.registry import get_parser
from src.indexing.embedder import embed_texts
from src.indexing.chroma_store import upsert
from src.ignore_list import IGNORE_DIRS, IGNORE_EXTENSIONS, IGNORE_FILES

def walk_repository(repo_path: Path):
    """
    Walks a repository and yields valid file paths, skipping ignored directories and files.
    """
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
            
        # Check if it's inside an ignored directory
        # path.parts returns a tuple of the path components
        is_ignored_dir = any(ignored in path.parts for ignored in IGNORE_DIRS)
        if is_ignored_dir:
            continue
            
        # Check file extension and exact name
        if path.suffix.lower() in IGNORE_EXTENSIONS or path.name in IGNORE_FILES:
            continue
            
        yield path

def index_all_repositories():
    """
    The orchestrator. Walks all cloned repos, parses them, embeds chunks, and stores in Chroma.
    """
    repos_dir = Path("knowledge_base/repos")
    if not repos_dir.exists():
        print("No repositories found to index.")
        return
        
    for repo_path in repos_dir.iterdir():
        if not repo_path.is_dir():
            continue
            
        repo_name = repo_path.name
        print(f"\nIndexing repository: {repo_name}")
        
        chunks_indexed = 0
        
        for file_path in walk_repository(repo_path):
            parser = get_parser(file_path)
            
            if parser is None:
                # No parser registered for this file type
                continue
                
            try:
                # Call the correct parser
                chunks = parser(file_path, repo_name)
                
                if not chunks:
                    continue
                    
                # Extract text for embeddings
                texts_to_embed = [chunk.content for chunk in chunks]
                
                # Embed chunks
                embeddings = embed_texts(texts_to_embed)
                
                # Store in ChromaDB
                upsert(chunks, embeddings)
                
                chunks_indexed += len(chunks)
                print(f"  Processed {file_path.name} ({len(chunks)} chunks)")
                
            except Exception as e:
                print(f"  Failed to process {file_path.name}: {e}")
                
        print(f"Finished {repo_name}. Total chunks indexed: {chunks_indexed}")
