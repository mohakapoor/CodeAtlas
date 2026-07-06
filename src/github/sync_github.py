import os
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timezone
from src.utils import SyncResult
from src.github.manifest import load_manifest, save_manifest

def run_cmd(cmd: list[str], cwd: str = None) -> str:
    """Run a shell command and return its output as a string."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Command failed: {' '.join(cmd)}\nError: {result.stderr}")
    return result.stdout.strip()

def fetch_github_repos(username: str, topic: str) -> list[dict]:
    """Fetch public repos for the user that have the target topic."""
    url = f"https://api.github.com/users/{username}/repos"
    headers = {"Accept": "application/vnd.github+json"}
    repos = []
    page = 1
    while True:
        response = requests.get(url, headers=headers, params={"per_page": 100, "page": page})
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        for repo in data:
            if not repo.get('private', False) and topic in repo.get('topics', []):
                repos.append(repo)
        page += 1
    return repos

def get_available_branches(repo_path: str) -> list[str]:
    """Get all available remote branches in the repository."""
    try:
        output = run_cmd(["git", "branch", "-r"], cwd=repo_path)
        branches = []
        for line in output.split('\n'):
            line = line.strip()
            if not line or '->' in line:
                continue
            if line.startswith('origin/'):
                branches.append(line.replace('origin/', ''))
        return branches
    except Exception as e:
        print(f"Warning: Could not fetch branches for {repo_path}: {e}")
        return []

def get_changed_files(repo_path: str, old_sha: str, new_sha: str) -> list[str]:
    """
    Returns a list of changed files between two commits.
    If old_sha is empty, implies everything is changed.
    """
    if not old_sha:
        return ["*"]
    if old_sha == new_sha:
        return []
    
    try:
        # --name-only returns just the file paths that changed
        output = run_cmd(["git", "diff", "--name-only", old_sha, new_sha], cwd=repo_path)
        return [f.strip() for f in output.split('\n') if f.strip()]
    except Exception as e:
        print(f"Warning: Could not compute git diff for {repo_path}: {e}")
        return ["*"]

def clone_repository(clone_url: str, repo_path: str, default_branch: str) -> tuple[str, str]:
    """
    Clones a repository and checks out the appropriate branch.
    Returns (tracked_branch, current_sha).
    """
    print(f"[+] Cloning new repository...")
    run_cmd(["git", "clone", clone_url, repo_path])
    
    branches = get_available_branches(repo_path)
    tracked_branch = default_branch
    
    if "prod" in branches:
        run_cmd(["git", "checkout", "prod"], cwd=repo_path)
        tracked_branch = "prod"
    elif tracked_branch in branches:
        run_cmd(["git", "checkout", tracked_branch], cwd=repo_path)
        
    current_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path)
    return tracked_branch, current_sha

def pull_repository(repo_path: str, tracked_branch: str) -> tuple[str, str]:
    """
    Pulls latest changes for an existing repository.
    Returns (old_sha, current_sha).
    """
    print(f"[*] Syncing existing repository (branch: {tracked_branch})...")
    old_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path)
    print(f"    Pulling latest changes...")
    run_cmd(["git", "pull", "origin", tracked_branch], cwd=repo_path)
    current_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path)
    return old_sha, current_sha

def sync_single_repo(repo: dict, username: str, base_dir: str) -> tuple[str, dict, list[str]]:
    """
    Manages the sync flow for one repository.
    Returns (status, global_entry, changed_files).
    """
    repo_name = repo['name']
    clone_url = repo['clone_url']
    repos_dir = os.path.join(base_dir, "repos")
    repo_path = os.path.join(repos_dir, repo_name)
    manifest_path = os.path.join(repo_path, "manifest.json")
    
    primary_lang = repo.get('language')
    languages = [primary_lang] if primary_lang else []
    now = datetime.now(timezone.utc).isoformat()
    
    tracked_branch = repo['default_branch']
    is_new = not os.path.exists(repo_path)
    
    # Load existing manifest if present
    manifest = load_manifest(repo_path)
    if not is_new:
        tracked_branch = manifest.get('tracked_branch', tracked_branch)
        
    old_sha = manifest.get('current_commit_sha', "")
    indexed_commit_sha = manifest.get('indexed_commit_sha', "")
    index_queue = manifest.get('index_queue', [])
    
    # Clone or Pull
    if is_new:
        tracked_branch, current_sha = clone_repository(clone_url, repo_path, tracked_branch)
        index_queue = ["*"]
    else:
        _, current_sha = pull_repository(repo_path, tracked_branch)
        if old_sha != current_sha:
            print(f"    Changes detected ({old_sha[:7]} -> {current_sha[:7]}).")
            if index_queue != ["*"]:
                diff_files = get_changed_files(repo_path, old_sha, current_sha)
                index_queue = list(set(index_queue + diff_files))
        else:
            print("    No new commits.")
            
    if is_new:
        status = "newly_cloned"
    elif index_queue:
        status = "updated"
    else:
        status = "unchanged"
        
    changed_files = index_queue
    
    branches = get_available_branches(repo_path)
    
    # Update Manifest
    manifest.update({
        "repository_name": repo_name,
        "owner": username,
        "tracked_branch": tracked_branch,
        "current_commit_sha": current_sha,
        "indexed_commit_sha": indexed_commit_sha,
        "index_queue": index_queue,
        "available_branches": branches,
        "topics": repo.get('topics', []),
        "languages": languages,
        "last_sync_timestamp": now
    })
    
    save_manifest(repo_path, manifest)
        
    # Prepare global manifest entry
    global_entry = {
        "name": repo_name,
        "local_path": os.path.relpath(repo_path, base_dir).replace('\\', '/'),
        "manifest_path": os.path.relpath(manifest_path, base_dir).replace('\\', '/'),
        "tracked_branch": tracked_branch,
        "current_commit_sha": current_sha,
        "last_sync_timestamp": now
    }
    
    return status, global_entry, changed_files

def sync_repositories(username: str, topic: str, base_dir: str = "knowledge_base") -> list[SyncResult]:
    """
    The main orchestrator. Fetches GitHub repos, syncs them all, 
    and returns a list of repo names that require re-indexing.
    """
    print(f"Starting synchronization for user '{username}' (topic: '{topic}')")
    
    repos_dir = os.path.join(base_dir, "repos")
    global_manifest_path = os.path.join(base_dir, "manifest.json")
    
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(repos_dir, exist_ok=True)
    
    repos = fetch_github_repos(username, topic)
    print(f"Discovered {len(repos)} repositories matching criteria.\n")
    
    summary = {
        "discovered": len(repos),
        "newly_cloned": 0,
        "updated": 0,
        "unchanged": 0,
        "requires_reindex": 0
    }
    
    global_manifest_data = {
        "last_sync_timestamp": datetime.now(timezone.utc).isoformat(),
        "repositories": []
    }
    
    sync_results = []
    
    for repo in repos:
        repo_name = repo['name']
        print(f"\nProcessing {repo_name}...")
        try:
            status, global_entry, changed_files = sync_single_repo(repo, username, base_dir)
            
            summary[status] += 1
            if status in ["newly_cloned", "updated"]:
                summary["requires_reindex"] += 1
                
                # Create a rich SyncResult for ingest.py to consume
                # We only append repos that actually have changes!
                sync_results.append(
                    SyncResult(
                        repo_name=repo_name,
                        repo_path=Path(base_dir) / "repos" / repo_name,
                        status=status,
                        changed_files=changed_files
                    )
                )
                
            global_manifest_data["repositories"].append(global_entry)
        except Exception as e:
            print(f"[!] Error syncing {repo_name}: {e}")
            
    with open(global_manifest_path, 'w') as f:
        json.dump(global_manifest_data, f, indent=2)
        
    print("\n--- Synchronization Summary ---")
    print(f"Repositories discovered:       {summary['discovered']}")
    print(f"Newly cloned repositories:     {summary['newly_cloned']}")
    print(f"Updated repositories:          {summary['updated']}")
    print(f"Unchanged repositories:        {summary['unchanged']}")
    print(f"Repositories req. re-indexing: {summary['requires_reindex']}")
    print("-------------------------------")
    
    return sync_results

def main():
    # Example local test execution
    import dotenv
    dotenv.load_dotenv()
    
    # You would typically pass these in from your orchestrator
    test_user = "mohakapoor"
    test_topic = "knowledge-base"
    
    sync_repositories(test_user, test_topic)

if __name__ == "__main__":
    main()
