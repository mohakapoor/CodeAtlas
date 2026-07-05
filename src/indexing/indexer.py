from pathlib import Path
from src.parsing.registry import get_parser
from src.indexing.chroma_store import upsert, delete_file
from src.ignore_list import IGNORE_DIRS, IGNORE_EXTENSIONS, IGNORE_FILES

BATCH_SIZE = 100


def walk_repository(repo_path: Path):
    """
    Walks a repository and yields valid file paths, skipping ignored directories and files.
    """
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
            
        # Check if it's inside an ignored directory
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
            
        # Check file extension and exact name
        if path.suffix.lower() in IGNORE_EXTENSIONS or path.name in IGNORE_FILES:
            continue
            
        yield path

def index_file(repo_name: str, file_path: Path, reindex: bool = False) -> tuple[int, int]:
    """
    Parses a file and upserts the chunks. 
    If reindex=True, deletes existing chunks first (useful for incremental updates).
    """
    parser = get_parser(file_path)
    if parser is None:
        return 0, 0

    try:
        # 1. Optionally delete old chunks from ChromaDB to avoid duplicates
        if reindex:
            delete_file(repo_name, file_path.as_posix())
        
        # 2. Parse the file
        chunks = parser(file_path, repo_name)
        if not chunks:
            return 0, 1
            
        # 3. Upsert the new chunks
        indexed_count = upsert(chunks)
        print(f"  Updated {file_path.name} ({indexed_count} chunks)")
        return indexed_count, 1
        
    except Exception as e:
        print(f"  Failed to update {file_path.name}: {e}")
        return 0, 0

def index_repository(repo_path: Path) -> tuple[int, int]:
    """
    Walks a single cloned repo, parses it, and stores the chunks in Chroma.
    """
    if not repo_path.exists() or not repo_path.is_dir():
        print(f"Repository path {repo_path} is invalid.")
        return 0, 0
        
    repo_name = repo_path.name
    print(f"\nIndexing repository: {repo_name}")
    
    all_chunks = []
    files_parsed = 0
    
    # 1. Parse all files and accumulate chunks
    for file_path in walk_repository(repo_path):
        parser = get_parser(file_path)
        if parser is not None:
            try:
                chunks = parser(file_path, repo_name)
                if chunks:
                    all_chunks.extend(chunks)
                print(f"  Parsed {file_path.name}")
                files_parsed += 1
            except Exception as e:
                print(f"  Failed to parse {file_path.name}: {e}")
                
    # 2. Batch upsert into ChromaDB
    chunks_indexed = 0
    
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i:i + BATCH_SIZE]
        try:
            indexed = upsert(batch)
            chunks_indexed += indexed
            print(f"  Upserted batch {i//BATCH_SIZE + 1} ({indexed} chunks)")
        except Exception as e:
            print(f"  Failed to upsert batch {i//BATCH_SIZE + 1}: {e}")
            
    print(f"Finished {repo_name}. Total chunks indexed: {chunks_indexed}")
    return chunks_indexed, files_parsed
