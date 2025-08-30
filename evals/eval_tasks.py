import argparse
import asyncio
import datetime
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import datasets
import pandas as pd
from datasets import Dataset
from dotenv import load_dotenv
from tqdm import tqdm
from deepsearch.utils import extract_content
from deepsearch.graph import graph

load_dotenv()

APPEND_ANSWER_LOCK = threading.Lock()

reranker_ip = os.getenv("RERANKER_SERVER_HOST_IP")
reranker_port = os.getenv("RERANKER_SERVER_PORT")
openai_api_key = os.getenv("LAMBDA_API_KEY")

if openai_api_key:
    model_id = "deepseek-r1-671b"
else:
    model_id = "gemini-2.5-pro"

if reranker_ip:
    reranker = "local"
else:
    reranker = "jina"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Runs an agent powered by the given model.")
    parser.add_argument(
        "--eval-tasks",
        type=str,
        nargs="+",
        default=["./evals/datasets/frames_sample_set.csv"],
        help="List of evaluation task paths",
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=8,
        help="The number of processes to run in parallel",
    )
    parser.add_argument(
        "--batch-save-size",
        type=int,
        default=10,
        help="Number of completed answers to batch before saving to file",
    )
    return parser.parse_args()


def load_eval_dataset(eval_tasks: list):
    eval_ds = {}
    for task_path in eval_tasks:
        task_name = task_path.split("/")[-1][:-4]
        df = pd.read_csv(task_path)
        dataset = Dataset.from_pandas(df)
        eval_ds[task_name] = dataset
    return eval_ds

def append_answer(entry: dict, jsonl_file: str) -> None:
    """Legacy function - kept for compatibility, but prefer batch_append_answers"""
    jsonl_file = Path(jsonl_file)
    jsonl_file.parent.mkdir(parents=True, exist_ok=True)
    with APPEND_ANSWER_LOCK, open(jsonl_file, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")
    assert os.path.exists(jsonl_file), "File not found!"
    print(f"✅ Saved answer to: {jsonl_file}")
    print(f"   Question: {entry['original_question'][:100]}...")
    print(f"   Answer: {entry['answer'][:100]}...")

def batch_append_answers(entries: list[dict], jsonl_file: str) -> None:
    """Append multiple answers to JSONL file in a single operation"""
    if not entries:
        return
    
    jsonl_file = Path(jsonl_file)
    jsonl_file.parent.mkdir(parents=True, exist_ok=True)
    with APPEND_ANSWER_LOCK, open(jsonl_file, "a", encoding="utf-8") as fp:
        for entry in entries:
            fp.write(json.dumps(entry) + "\n")
    assert os.path.exists(jsonl_file), "File not found!"
    
    print(f"💾 Batch saved {len(entries)} answers to: {jsonl_file}")
    for i, entry in enumerate(entries):
        print(f"   [{i+1}] Q: {entry['original_question'][:80]}...")
        print(f"       A: {entry['answer'][:80]}...")


def load_answered_questions(jsonl_file: str) -> set[str]:
    """Load already-answered questions from a JSONL file into a set for fast lookup."""
    answered_questions: set[str] = set()
    if not os.path.exists(jsonl_file):
        return answered_questions

    try:
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    question = obj.get("original_question")
                    if question is not None:
                        answered_questions.add(question)
                except Exception:
                    # Skip malformed lines
                    continue
    except Exception as e:
        print(f"⚠️ Could not read existing answers file: {e}")

    return answered_questions

def run_with_timeout(func, timeout):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            return "Timed Out"

async def answer_single_question(example, answers_file=None):
    """Answer a single question and return the result instead of immediately saving"""
    augmented_question = example["question"]

    TIMEOUT_SECONDS = 300  # 5 minutes timeout

    async def get_agent_response():
        res = await graph.ainvoke({
            "task": augmented_question,
            "plan_string": None,
            "steps": [],
            "results": {},
            "result": None,
            "intermediate_result": None,
            "search_query": None,
            "needs_replan": False,
            "replan_iter": 0,
            "max_replan_iter": 2
        }, {"recursion_limit": 40})

        print(res)
        print(res["plan_string"])
        print(res["results"])

        response = res["result"]
        answer = extract_content(response, "answer")
        if answer is None:
             answer = "Failed without an answer!"
        return answer
    try:
        answer = await asyncio.wait_for(get_agent_response(), timeout=TIMEOUT_SECONDS)
    except Exception as e:
        print("Error on ", augmented_question, e)
        answer = "Exception occurred"

    annotated_example = {
        "model_id": model_id,
        "original_question": example["question"],
        "answer": answer,
        "true_answer": example["true_answer"],
    }
    
    # Return the result instead of immediately saving
    return annotated_example

def answer_sync(example):
        return asyncio.run(answer_single_question(example))

def answer_questions(
    eval_ds,
    output_dir: str = "output",
    parallel_workers: int = 32,
    batch_save_size: int = 10,
):
    # Create directory structure: output/model_id/reranker/task
    model_dir = model_id.replace('/', '__')
    
    for task in eval_ds:
        task_dir = os.path.join(output_dir, model_id, reranker, task)
        os.makedirs(task_dir, exist_ok=True)
        
        file_name = f"{task_dir}/{model_id}__{reranker}__{task}.jsonl"
        print(f"\n🚀 Starting processing for task: {task}")
        print(f"📁 Output file: {file_name}")
        print(f"📍 Full path: {os.path.abspath(file_name)}")
        answered_questions = load_answered_questions(file_name)
        if os.path.exists(file_name):
            print(f"📋 Found {len(answered_questions)} already answered questions, skipping them")
        else:
            print(f"📄 Creating new output file")

        # Deduplicate within the dataset and filter out previously answered
        dataset_seen: set[str] = set()
        duplicates_in_dataset = 0
        examples_todo = []
        for example in eval_ds[task]:
            q = example["question"]
            if q in answered_questions:
                continue
            if q in dataset_seen:
                duplicates_in_dataset += 1
                continue
            dataset_seen.add(q)
            examples_todo.append(example)

        print(f"⚡ Processing {len(examples_todo)} questions with {parallel_workers} parallel workers.")
        print(f"💾 Using batch saving: will save every {batch_save_size} completed answers")
        if duplicates_in_dataset > 0:
            print(f"📎 Skipped {duplicates_in_dataset} duplicate questions found in the dataset")

        # Batch saving: collect answers and save every batch_save_size completions
        answer_buffer = []
        completed_count = 0
        BATCH_SIZE = batch_save_size
        run_seen_questions: set[str] = set()
        
        with ThreadPoolExecutor(max_workers=parallel_workers) as exe:
            futures = [
                exe.submit(answer_sync, example) 
                for example in examples_todo
            ]
            
            for f in tqdm(as_completed(futures), total=len(examples_todo), desc="Processing tasks"):
                try:
                    result = f.result()
                    if result:  # Only add valid results
                        q = result.get("original_question") if isinstance(result, dict) else None
                        if q is None:
                            continue
                        if q in answered_questions or q in run_seen_questions:
                            # Skip duplicates already answered or processed in this run
                            continue
                        run_seen_questions.add(q)
                        answer_buffer.append(result)
                        completed_count += 1
                        
                        # Save batch when we reach BATCH_SIZE
                        if len(answer_buffer) >= BATCH_SIZE:
                            batch_append_answers(answer_buffer, file_name)
                            print(f"🔄 Progress: {completed_count}/{len(examples_todo)} completed")
                            answer_buffer.clear()
                            
                except Exception as e:
                    print(f"❌ Error processing result: {e}")
            
            # Save any remaining answers in the buffer
            if answer_buffer:
                batch_append_answers(answer_buffer, file_name)
                print(f"🔄 Final batch: {len(answer_buffer)} remaining answers saved")

        print(f"✅ All {len(examples_todo)} tasks processed for {task}!")
        print(f"📊 Output saved to: {os.path.abspath(file_name)}")
        
        # Show final file stats
        if os.path.exists(file_name):
            with open(file_name, "r") as f:
                total_lines = sum(1 for _ in f)
            print(f"📈 File now contains {total_lines} total entries")


if __name__ == "__main__":
    args = parse_arguments()

    eval_ds = load_eval_dataset(args.eval_tasks)
    answer_questions(
        eval_ds,
        parallel_workers=args.parallel_workers,
        batch_save_size=args.batch_save_size,
    )
