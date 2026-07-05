from dataclasses import dataclass
from pathlib import Path

@dataclass 
class Chunk:
    id: str
    content :str
    metadata : dict


@dataclass
class SyncResult:
    repo_name: str
    repo_path: Path 
    status: str 
    changed_files: list[str] | None