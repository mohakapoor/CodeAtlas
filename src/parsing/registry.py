from src.parsing.pyparser import parse_py
from src.parsing.mdparser import parse_md
from src.parsing.textparser import parse_text

# The Registry Pattern: Mapping extensions to their parsing functions
PARSERS = {
    ".py": parse_py,
    ".md": parse_md,
    ".txt": parse_text,
    ".json": parse_text,
    ".yaml": parse_text,
    ".yml": parse_text,
    ".csv": parse_text,
    ".ini": parse_text,
    ".toml": parse_text,
    ".log": parse_text,
}

def get_parser(file_path):
    """
    Returns the appropriate parsing function for a given file extension,
    or None if no parser is registered for that extension.
    """
    ext = file_path.suffix.lower()
    
    # Special handling for Dockerfiles which lack standard extensions
    if "dockerfile" in file_path.name.lower():
        return parse_text
        
    return PARSERS.get(ext)
