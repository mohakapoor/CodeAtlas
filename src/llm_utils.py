from transformers import AutoTokenizer
import time 

_tokenizer = None

def get_hf_token_count(text: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> tuple[int,float]:
    s =time.time()
    global _tokenizer
    
    if not text:
        return (0,0.0)
        
    try:
        if _tokenizer is None:
            _tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokens = _tokenizer.encode(text, add_special_tokens=True)
        e = time.time()
        return (len(tokens), e - s)
    except Exception as e:
        print(f"Error counting tokens with {model_name}: {e}")
        return 0,0.0


def main():
    print(get_hf_token_count("Hello, how are you?"))


if __name__ == "__main__":
    main()
    