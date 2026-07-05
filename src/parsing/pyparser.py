
import ast
from src.utils import Chunk
from pathlib import Path


def parse_py(file_path,repo):
    TYPE_MAP = {
        ast.FunctionDef: "function",
        ast.AsyncFunctionDef: "async_function",
        ast.ClassDef: "class",
    }
    path = Path(file_path)
    relative = file_path.as_posix()
    
    base_metadata = {
        "path": str(file_path),
        "filename": path.name,
        "repo": repo,
        "language": "python"
    }
    
    chunks = []
    chunk_idx = 0
    module_buffer = []
    module_start = None
    module_end = None
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()

    



    for node in tree.body:
        start = node.lineno
        end = node.end_lineno

        node_source = "\n".join(lines[start - 1:end])

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):

            if module_buffer:

                t = "\n".join(module_buffer)
                module_buffer.clear()
                
                chunk_id = f"{repo}:{relative}:{chunk_idx}"
                meta = base_metadata.copy()
                meta.update({
                    "type": "Module",
                    "start_line": module_start if module_start is not None else "None",
                    "end_line": module_end if module_end is not None else "None",
                    "symbol": "None",
                    "chunk_idx": chunk_idx,
                    "size": len(t)
                })
                chunk_idx += 1
                chunks.append(
                    Chunk(id=chunk_id, content=t, metadata=meta)
                )
                module_start = None
                module_end = None

            # Print the function/class
            chunk_id = f"{repo}:{relative}:{chunk_idx}"
            meta = base_metadata.copy()
            meta.update({
                "type": TYPE_MAP[type(node)],
                "start_line": start,
                "end_line": end,
                "symbol": node.name or "None",
                "chunk_idx": chunk_idx,
                "size": len(node_source)
            })
            chunk_idx += 1
            
            chunks.append(
                Chunk(id=chunk_id, content=node_source, metadata=meta)
            )

        else:
            # Accumulate top-level code
            module_buffer.append(node_source)
            if module_start is None:
                module_start = start
            module_end = end

    # Flush any remaining module code at the end
    if module_buffer:
        chunk_id = f"{repo}:{relative}:{chunk_idx}"
        meta = base_metadata.copy()
        t = "\n".join(module_buffer)
        meta.update({
            "type": "Module",
            "start_line": module_start if module_start is not None else "None",
            "end_line": module_end if module_end is not None else "None",
            "symbol": "None",
            "chunk_idx": chunk_idx,
            "size": len(t)
        })
        chunk_idx += 1
        chunks.append(
            Chunk(id=chunk_id, content=t, metadata=meta)
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
    test_path = Path("src/parsing/test.py")
    parsed_chunks = parse_py(file_path=test_path, repo='intrusion')
    print_chunks(parsed_chunks)