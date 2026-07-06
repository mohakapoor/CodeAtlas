import json
from pathlib import Path

def load_manifest(repo_path: Path | str) -> dict:
    """Loads the manifest.json for a given repository."""
    manifest_path = Path(repo_path) / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {}

def save_manifest(repo_path: Path | str, data: dict) -> None:
    """Saves data back into the manifest.json for a given repository."""
    manifest_path = Path(repo_path) / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(data, f, indent=2)

def update_manifest_queue(repo_path: Path | str, file_to_remove: str = None, clear_all: bool = False):
    """
    Pops files off the index_queue in the manifest upon successful ingestion.
    If the queue empties completely, it advances the indexed_commit_sha.
    """
    data = load_manifest(repo_path)
    if not data:
        return
        
    if clear_all:
        data["index_queue"] = []
    elif file_to_remove and "index_queue" in data and file_to_remove in data["index_queue"]:
        data["index_queue"].remove(file_to_remove)
        
    # If the queue is empty, we are fully caught up to current_commit_sha!
    if not data.get("index_queue"):
        data["indexed_commit_sha"] = data.get("current_commit_sha", "")
        
    save_manifest(repo_path, data)
