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

    # Filter out markdown and text queries to evaluate pure code retrieval
    original_len = len(dataset)
    dataset = [tc for tc in dataset if tc.get("path") is None or not tc.get("path").endswith((".md", ".txt"))]
    filtered_out = original_len - len(dataset)

    print("Initializing CodeOnly Retriever...")
    retriever = CodeOnlyRetriever()
    
    total_queries = len(dataset)
    if total_queries == 0:
        print("Dataset is empty.")
        return

    print(f"\nFiltered out {filtered_out} markdown/text queries.")
    print(f"Starting Evaluation for {total_queries} pure-code queries...\n")
    
    hits = 0
    mrr_sum = 0.0
    
    start_time = time.time()
    
    for i, test_case in enumerate(dataset, 1):
        query = test_case["query"]
        expected_path = test_case["path"]
        target_repos = test_case["repo"]
        
        # We can add a filter to only search within the target repo, 
        # or we can search globally to make it a harder, more realistic test!
        # Here we'll search globally to test how well it distinguishes repos.
        results = retriever.retrieve(query, k=3)
        
        # Extract the retrieved paths
        # Note: metadata contains 'path' and 'repo'
        retrieved_docs = []
        for doc in results:
            doc_repo = doc.metadata.get("repo", "")
            doc_path = doc.metadata.get("path", "")
            retrieved_docs.append((doc_repo, doc_path))
            
        # Check for a match
        match_rank = 0
        is_repo_level_query = test_case.get("category") in ["multi_repo", "repository_recommendation"]
        found_repos = set()
        
        for rank, (repo, path) in enumerate(retrieved_docs, 1):
            norm_path = path.replace('\\', '/')
            
            if repo in target_repos:
                # If it's a repo-level query, finding any file in the correct repo is a hit
                if is_repo_level_query:
                    found_repos.add(repo)
                    if match_rank == 0:
                        match_rank = rank
                # Otherwise, it must match the expected path
                elif expected_path is not None and norm_path.endswith(expected_path):
                    if match_rank == 0:
                        match_rank = rank
                
        if match_rank > 0:
            hits += 1
            mrr_sum += 1.0 / match_rank
            
            # For multi-repo queries, show how many of the target repos were found
            if is_repo_level_query and len(target_repos) > 1:
                found_str = f" (Found {len(found_repos)}/{len(target_repos)} repos)"
            else:
                found_str = ""
                
            print(f"[{i}/{total_queries}] ✅ HIT (Rank {match_rank}){found_str}: '{query}' -> {expected_path or target_repos}")
        else:
            print(f"[{i}/{total_queries}] ❌ MISS: '{query}'")
            print(f"    Expected: {target_repos} {expected_path}")
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
