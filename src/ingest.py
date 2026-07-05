# from src.github.sync_github import sync_repositories
from src.indexing.indexer import index_all_repositories

def main():
    print("Starting ingestion pipeline...")
    
    # Step 1: Sync all repositories from GitHub
    # sync_repositories() 
    
    print("Sync complete. Beginning indexing...")
    
    # Step 2: Index everything
    index_all_repositories()
    
    print("Ingestion pipeline complete!")

if __name__ == "__main__":
    main()
