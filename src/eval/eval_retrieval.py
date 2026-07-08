import json
import time
from pathlib import Path
from src.retrieval.retrievers import CodeOnlyRetriever

def evaluate_retrieval():
    eval_file = Path("src/eval/eval_set.json")
    if not eval_file.exists():
        print(f"Error: Could not find {eval_file}")
        return

    with open(eval_file, "r") as f:
        dataset = json.load(f)

    print("Initializing CodeOnly Retriever...")
    retriever = CodeOnlyRetriever()
    
    total_queries = len(dataset)
    if total_queries == 0:
        print("Dataset is empty.")
        return

    print(f"\nStarting Evaluation for {total_queries} queries...\n")
    
    hits = 0
    mrr_sum = 0.0
    
    start_time = time.time()
    
    for i, test_case in enumerate(dataset, 1):
        query = test_case["query"]
        expected_path = test_case["path"]
        target_repo = test_case["repo"]
        
        # We can add a filter to only search within the target repo, 
        # or we can search globally to make it a harder, more realistic test!
        # Here we'll search globally to test how well it distinguishes repos.
        results = retriever.retrieve(query, k=5)
        
        # Extract the retrieved paths
        # Note: metadata contains 'path' and 'repo'
        retrieved_docs = []
        for doc in results:
            doc_repo = doc.metadata.get("repo", "")
            doc_path = doc.metadata.get("path", "")
            retrieved_docs.append((doc_repo, doc_path))
            
        # Check for a match
        # We consider it a match if both the repo and the path match the expectation
        match_rank = 0
        for rank, (repo, path) in enumerate(retrieved_docs, 1):
            # Normalize slashes for Windows compatibility
            norm_path = path.replace('\\', '/')
            if repo == target_repo and (expected_path is not None and norm_path.endswith(expected_path)):
                match_rank = rank
                break
                
        if match_rank > 0:
            hits += 1
            mrr_sum += 1.0 / match_rank
            print(f"[{i}/{total_queries}] ✅ HIT (Rank {match_rank}): '{query}' -> {expected_path}")
        else:
            print(f"[{i}/{total_queries}] ❌ MISS: '{query}'")
            print(f"    Expected: [{target_repo}] {expected_path}")
            print(f"    Got: {retrieved_docs}")

    elapsed = time.time() - start_time
    
    hit_rate = (hits / total_queries) * 100
    mrr = mrr_sum / total_queries
    
    print("\n" + "="*40)
    print("      RETRIEVAL EVALUATION RESULTS")
    print("="*40)
    print(f"Total Queries : {total_queries}")
    print(f"Hit Rate @ 5  : {hit_rate:.1f}% ({hits}/{total_queries})")
    print(f"MRR @ 5       : {mrr:.3f}")
    print(f"Elapsed Time  : {elapsed:.1f} s")
    print("="*40 + "\n")

if __name__ == "__main__":
    evaluate_retrieval()
