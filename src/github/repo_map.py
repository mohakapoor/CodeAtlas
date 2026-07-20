import os
from pathlib import Path
from src.utils import Chunk
from src.ignore_list import IGNORE_DIRS, IGNORE_EXTENSIONS, IGNORE_FILES

def generate_tree(dir_path: Path, prefix: str = "", is_last: bool = True) -> list[str]:
    """Recursively generates a tree-like string representation of the directory."""
    tree_lines = []
    
    try:
        entries = list(dir_path.iterdir())
    except PermissionError:
        return []

    # Filter out ignored files/dirs
    valid_entries = []
    for entry in entries:
        if entry.is_dir() and entry.name in IGNORE_DIRS:
            continue
        if entry.is_file():
            if entry.name in IGNORE_FILES or entry.suffix.lower() in IGNORE_EXTENSIONS:
                continue
        valid_entries.append(entry)
        
    # Sort directories first, then alphabetically
    valid_entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
    
    count = len(valid_entries)
    for i, entry in enumerate(valid_entries):
        is_last_entry = (i == count - 1)
        connector = "└── " if is_last_entry else "├── "
        
        tree_lines.append(f"{prefix}{connector}{entry.name}")
        
        if entry.is_dir():
            extension = "    " if is_last_entry else "│   "
            tree_lines.extend(generate_tree(entry, prefix + extension, is_last_entry))
            
    return tree_lines

def build_portfolio_graph(repos_dir: str | Path, output_file: str | Path | None = None) -> Chunk | None:
    """
    Builds a markdown string of the entire portfolio's file structure and wraps it in a Chunk.
    Optionally writes the markdown to a file on disk.
    """
    repos_dir = Path(repos_dir)
    if not repos_dir.exists() or not repos_dir.is_dir():
        print("Repos directory not found for graph generation.")
        return None
        
    lines = ["# User Repository Map\n"]
    lines.append("This document maps all repositories, folders, and files in the knowledge base.")
    lines.append("Use this to understand the high-level structure of the portfolio.\n")
    
    repos = [d for d in repos_dir.iterdir() if d.is_dir()]
    repos.sort(key=lambda x: x.name.lower())
    
    for repo in repos:
        lines.append(f"## [{repo.name}]")
        lines.append("```text")
        repo_tree = generate_tree(repo)
        if repo_tree:
            lines.extend(repo_tree)
        else:
            lines.append("└── (Empty or ignored)")
        lines.append("```\n")
        
    content = "\n".join(lines)
    
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Failed to write portfolio graph to {output_file}: {e}")
            
    chunk = Chunk(
        id="global_portfolio_graph",
        content=content,
        metadata={
            "repo": "global",
            "path": "portfolio_graph",
            "language": "markdown",
            "type": "global_graph"
        }
    ) 
    
    return chunk
