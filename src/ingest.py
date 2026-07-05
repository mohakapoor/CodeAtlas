import os
import time
from pathlib import Path
from src.indexing.indexer import index_repository, index_file
from src.github.sync_github import sync_repositories

def main():
    print("Starting ingestion pipeline...")
    
    start_time = time.time()
    
    # Step 1: Sync all repositories from GitHub
    username = os.getenv("GITHUB_USERNAME", "mohakapoor")
    topic = os.getenv("GITHUB_TOPIC", "knowledge-base")
    
    sync_results = sync_repositories(username, topic)
    
    print("\nSync complete. Beginning indexing routing...")
    
    total_chunks = 0
    total_files = 0
    total_repos = len(sync_results)
    
    # Step 2: Route ingestion based on SyncResult
    from src.indexing.chroma_store import delete_file
    
    for result in sync_results:
        print(f"\nEvaluating ingestion for {result.repo_name}...")
        
        if result.status == "newly_cloned":
            # Bulk index everything
            chunks, files = index_repository(result.repo_path)
            total_chunks += chunks
            total_files += files
            
        elif result.changed_files:
            # Incremental single-file indexing
            print(f"Routing {len(result.changed_files)} changed files to incremental indexer...")
            for file_rel_path in result.changed_files:
                abs_path = result.repo_path / file_rel_path
                
                if abs_path.exists():
                    chunks, files = index_file(result.repo_name, abs_path, reindex=True)
                    total_chunks += chunks
                    total_files += files
                else:
                    # File was deleted in git pull
                    delete_file(result.repo_name, abs_path.as_posix())
                    print(f"  Removed deleted file {file_rel_path} from index")
                    
    elapsed = time.time() - start_time
    
    print("\n----------------------------------")
    print(f"Repositories indexed : {total_repos}")
    print(f"Files parsed         : {total_files:,}")
    print(f"Chunks stored        : {total_chunks:,}")
    print(f"Elapsed              : {elapsed:.1f} s")
    print("----------------------------------")

if __name__ == "__main__":
    main()
