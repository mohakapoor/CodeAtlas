import os
import json
import subprocess
import requests
from datetime import datetime, timezone

USERNAME = "mohakapoor"
TOPIC = "knowledge-base"
BASE_DIR = "knowledge_base"
REPOS_DIR = os.path.join(BASE_DIR, "repos")
GLOBAL_MANIFEST_PATH = os.path.join(BASE_DIR, "manifest.json")

def run_cmd(cmd, cwd=None):
    """Run a shell command and return its output as a string."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Command failed: {' '.join(cmd)}\nError: {result.stderr}")
    return result.stdout.strip()

def get_repos():
    """Fetch public repos for the user that have the target topic."""
    url = f"https://api.github.com/users/{USERNAME}/repos"
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
            if not repo.get('private', False) and TOPIC in repo.get('topics', []):
                repos.append(repo)
        page += 1
    return repos

def get_available_branches(repo_path):
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

def sync_repo(repo):
    """Sync a single repository (clone or pull)."""
    repo_name = repo['name']
    clone_url = repo['clone_url']
    repo_path = os.path.join(REPOS_DIR, repo_name)
    manifest_path = os.path.join(repo_path, "manifest.json")
    
    # Use primary language for now to avoid N+1 API calls; full extraction can happen during indexing
    primary_lang = repo.get('language')
    languages = [primary_lang] if primary_lang else []
    
    now = datetime.now(timezone.utc).isoformat()
    
    status = "unchanged"
    requires_reindex = False
    tracked_branch = repo['default_branch']
    current_sha = ""
    
    is_new = not os.path.exists(repo_path)
    
    if is_new:
        print(f"[+] Cloning new repository: {repo_name}...")
        run_cmd(["git", "clone", clone_url, repo_path])
        
        branches = get_available_branches(repo_path)
        if "prod" in branches:
            run_cmd(["git", "checkout", "prod"], cwd=repo_path)
            tracked_branch = "prod"
        elif tracked_branch in branches:
            run_cmd(["git", "checkout", tracked_branch], cwd=repo_path)
            
        current_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path)
        status = "newly_cloned"
        requires_reindex = True
        
        manifest = {
            "repository_name": repo_name,
            "owner": USERNAME,
            "tracked_branch": tracked_branch,
            "current_commit_sha": current_sha,
            "available_branches": branches,
            "topics": repo.get('topics', []),
            "languages": languages,
            "last_sync_timestamp": now,
            "last_index_timestamp": None
        }
    else:
        print(f"[*] Syncing existing repository: {repo_name}...")
        # read existing manifest to get tracked branch if exists
        manifest = {}
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                try:
                    manifest = json.load(f)
                except json.JSONDecodeError:
                    pass
            tracked_branch = manifest.get('tracked_branch', tracked_branch)
            
        old_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path)
        print(f"    Pulling latest changes on branch '{tracked_branch}'...")
        run_cmd(["git", "pull", "origin", tracked_branch], cwd=repo_path)
        current_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_path)
        
        branches = get_available_branches(repo_path)
        
        if old_sha != current_sha:
            status = "updated"
            requires_reindex = True
            print(f"    Changes detected ({old_sha[:7]} -> {current_sha[:7]}).")
        else:
            status = "unchanged"
            print("    No new changes.")
            
        # Update manifest
        manifest.update({
            "repository_name": repo_name,
            "owner": USERNAME,
            "tracked_branch": tracked_branch,
            "current_commit_sha": current_sha,
            "available_branches": branches,
            "topics": repo.get('topics', []),
            "languages": languages,
            "last_sync_timestamp": now
        })
        
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
        
    global_entry = {
        "name": repo_name,
        "local_path": os.path.relpath(repo_path, BASE_DIR).replace('\\', '/'),
        "manifest_path": os.path.relpath(manifest_path, BASE_DIR).replace('\\', '/'),
        "tracked_branch": tracked_branch,
        "current_commit_sha": current_sha,
        "last_sync_timestamp": now
    }
    
    return status, requires_reindex, global_entry

def main():
    print(f"Starting synchronization for user '{USERNAME}' (topic: '{TOPIC}')")
    
    # Create necessary base directories
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(REPOS_DIR, exist_ok=True)
    
    repos = get_repos()
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
    
    for repo in repos:
        try:
            status, req_reindex, global_entry = sync_repo(repo)
            summary[status] += 1
            if req_reindex:
                summary["requires_reindex"] += 1
            global_manifest_data["repositories"].append(global_entry)
        except Exception as e:
            print(f"[!] Error syncing {repo['name']}: {e}")
            
    with open(GLOBAL_MANIFEST_PATH, 'w') as f:
        json.dump(global_manifest_data, f, indent=2)
        
    print("\n--- Synchronization Summary ---")
    print(f"Repositories discovered:       {summary['discovered']}")
    print(f"Newly cloned repositories:     {summary['newly_cloned']}")
    print(f"Updated repositories:          {summary['updated']}")
    print(f"Unchanged repositories:        {summary['unchanged']}")
    print(f"Repositories req. re-indexing: {summary['requires_reindex']}")
    print("-------------------------------")

if __name__ == "__main__":
    main()
