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
                
    from src.github.manifest import update_manifest_queue
    from src.indexing.chroma_store import delete_file
    
    for result in sync_results:
        print(f"\nEvaluating ingestion for {result.repo_name}...")
        
        if result.changed_files == ["*"]:
            # Bulk index everything
            chunks, files = index_repository(result.repo_path)
            total_chunks += chunks
            total_files += files
            update_manifest_queue(result.repo_path, clear_all=True)
            
        elif result.changed_files:
            # Incremental single-file indexing
            print(f"Routing {len(result.changed_files)} pending files to incremental indexer...")
            for file_rel_path in result.changed_files:
                abs_path = result.repo_path / file_rel_path
                
                try:
                    if abs_path.exists():
                        chunks, files = index_file(result.repo_name, abs_path, reindex=True)
                        total_chunks += chunks
                        total_files += files
                    else:
                        # File was deleted in git pull
                        delete_file(result.repo_name, abs_path.as_posix())
                        print(f"  Removed deleted file {file_rel_path} from index")
                        
                    # Pop from the queue immediately after success
                    update_manifest_queue(result.repo_path, file_to_remove=file_rel_path)
                except Exception as e:
                    print(f"  Error processing {file_rel_path}: {e}")
                    
    print("\nGenerating global portfolio graph...")
    try:
        from src.github.repo_map import build_portfolio_graph
        from src.indexing.chroma_store import delete_file, upsert
        
        repos_dir = Path("knowledge_base/repos")
        graph_file = Path("knowledge_base/portfolio_graph.md")
        graph_chunk = build_portfolio_graph(repos_dir, output_file=graph_file)
        
        if graph_chunk:
            delete_file("global", "portfolio_graph")
            upsert([graph_chunk])
            print("  Successfully generated and indexed portfolio graph.")
    except Exception as e:
        print(f"  Failed to generate portfolio graph: {e}")
        
    elapsed = time.time() - start_time
    
    print("\n----------------------------------")
    print(f"Repositories indexed : {total_repos}")
    print(f"Files parsed         : {total_files:,}")
    print(f"Chunks stored        : {total_chunks:,}")
    print(f"Elapsed              : {elapsed:.1f} s")
    print("----------------------------------")

if __name__ == "__main__":
    main()
