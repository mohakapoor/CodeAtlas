from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.utils import Chunk

def parse_text(file_path, repo,language = "text"):
    path = Path(file_path)
    relative = path.as_posix()
    
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = path.read_text(encoding="latin-1")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []
    
    chunks = []
    
    base_metadata = {
        "repo": repo,
        "path": relative,
        "filename": path.name,
        "language": language,
        "type": "text"
    }

    # check if the file is too small
    if len(source) <= 1000:
        chunk_id = f"{repo}:{relative}:0"
        meta = base_metadata.copy()
        meta["chunk_idx"] = 0
        meta["size"] = len(source)
        chunks.append(Chunk(id=chunk_id, content=source, metadata=meta))
        return chunks

    # Otherwise, we split it prioritizing paragraphs ("\n\n"), then lines ("\n")
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " ", ""],
        chunk_size=1000, 
        chunk_overlap=100
    )
    
    splits = text_splitter.split_text(source)
    
    for i, content in enumerate(splits):
        chunk_id = f"{repo}:{relative}:{i}"
        meta = base_metadata.copy()
        meta["chunk_idx"] = i
        meta["size"] = len(content)
        
        chunks.append(
            Chunk(id=chunk_id, content=content, metadata=meta)
        )
        
    return chunks

def print_chunks(chunks):
    for chunk in chunks:
        print(f"\n{'='*50}")
        print(f" ID: {chunk.id}")
        for key, value in chunk.metadata.items():
            print(f" {key.capitalize()}: {value}")
        print(f"{'-'*50}")
        print(chunk.content)
        print(f"{'='*50}")

if __name__ == "__main__":
    # Ensure test file exists
    test_path = Path("src/parsing/test.txt")
    if not test_path.exists():
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text("This is a simple text file.\n\nIt has a few paragraphs.\n\n" * 20, encoding="utf-8")
        
    parsed_chunks = parse_text(file_path=test_path, repo='intrusion')
    print_chunks(parsed_chunks)
