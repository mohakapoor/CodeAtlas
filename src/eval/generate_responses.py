import json
import time
import argparse
import random
from pathlib import Path
import os
import dotenv

from src.chat import CodeAtlasChat

def generate_checkpoint(sample_size=None, output_file="src/eval/test_dataset/generation_eval.json"):
    """
    Generates a checkpoint file containing query, context (with metadata), generated answer, 
    and ground truth. Does not perform any RAGAS evaluation.
    """
    dotenv.load_dotenv()
    
    eval_file = Path("src/eval/eval_set.json")

    with open(eval_file, "r") as f:
        data = json.load(f)

    if sample_size and sample_size < len(data):
        print(f"Randomly sampling {sample_size} questions from the dataset of {len(data)}...")
        random.seed(42)
        data = random.sample(data, sample_size)
    
    print("Initializing CodeAtlas Chat Engine...")
    chat_engine = CodeAtlasChat()
    
    questions = []
    answers = []
    contexts = []
    ground_truths = []
    relevant_files_list = []
    
    total_queries = len(data)
    print(f"\nStarting Generation for {total_queries} queries...\n")
    
    start_time = time.time()
    
    for i, test_case in enumerate(data, 1):
        query = test_case["query"]
        expected_gt = test_case.get("ground_truth", "")
        repos = test_case.get("repo", [])
        path = test_case.get("path")
        
        relevant_files = []
        if path:
            for r in repos:
                proper_path = os.path.normpath(os.path.join("knowledge_base", "repos", r, path))
                relevant_files.append(proper_path)
        
        print(f"[{i}/{total_queries}] Processing: {query}")
        
        try:
            # Fetch the raw docs independently
            docs = chat_engine.retriever.retrieve(query)
            
            # Format docs as a list of dicts: {"text": chunk, "metadata": metadata}
            doc_texts = [{"text": doc.page_content, "metadata": doc.metadata} for doc in docs]
            
            # Clear chat history
            chat_engine.session.clear()
            
            # Get the generated response
            result = chat_engine.ask(query)
            generated_response = result["response"]
            
            # Ensure response is a string
            if isinstance(generated_response, list):
                text_parts = [item.get("text", "") for item in generated_response if isinstance(item, dict)]
                generated_response = " ".join(text_parts)
            elif not isinstance(generated_response, str):
                generated_response = str(generated_response)
                
            questions.append(query)
            answers.append(generated_response)
            contexts.append(doc_texts)
            ground_truths.append(expected_gt)
            relevant_files_list.append(relevant_files)
            
            # Rate limit handling (Gemini Free Tier)
            if i < total_queries:
                time.sleep(5)
                
        except Exception as e:
            print(f"\n[!] API Error or Rate Limit hit at question {i}: {e}")
            print(f"We successfully generated {len(questions)} answers. Saving partial progress...")
            break
        
    generation_time = time.time() - start_time
    print(f"\nGeneration completed in {generation_time:.1f} seconds.")
    
    data_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
        "relevant_files": relevant_files_list
    }
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(data_dict, f, indent=4)
        
    print(f"Successfully saved generation data to {output_file}!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dataset for custom evaluation (JudgeKit)")
    parser.add_argument("--sample", type=int, default=None, help="Number of questions to sample")
    parser.add_argument("--output", type=str, default="src/eval/test_dataset/generation_eval.json", help="Output file name")
    args = parser.parse_args()
    
    generate_checkpoint(sample_size=args.sample, output_file=args.output)
