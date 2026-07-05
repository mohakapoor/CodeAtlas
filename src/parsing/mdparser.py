from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from src.utils import Chunk

def parse_md(file_path, repo):
    path = Path(file_path)
    relative = path.as_posix()
    
    base_metadata = {
        "path": str(file_path),
        "filename": path.name,
        "repo": repo,
        "language": "markdown"
    }
    
    source = path.read_text(encoding="utf-8")
    
    # Split by H1 and H2
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
    ]
    
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(source)
    
    # Run each heading split through RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=100
    )
    
    final_splits = text_splitter.split_documents(md_header_splits)
    
    chunks = []
    for chunk_idx, split in enumerate(final_splits):
        chunk_id = f"{repo}:{relative}:{chunk_idx}"
        
        meta = base_metadata.copy()
        
        # Extract headers and use the most specific one as the symbol
        h1 = split.metadata.get("Header 1")
        h2 = split.metadata.get("Header 2")
        
        meta.update({
            "type": "section",
            "start_line": None,
            "end_line": None,
            "h1": h1,
            "h2": h2,
            "symbol": h2 or h1,
            "chunk_idx": chunk_idx,
            "size": len(split.page_content)
        })
        
        chunks.append(
            Chunk(id=chunk_id, content=split.page_content, metadata=meta)
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
    test_path = Path("src/parsing/test.md")
    if test_path.exists():
        parsed_chunks = parse_md(file_path=test_path, repo='weathercli')
        print_chunks(parsed_chunks)
    else:
        print(f"Test file not found: {test_path}")
