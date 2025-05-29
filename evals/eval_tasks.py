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

from langchain_core.messages import HumanMessage
from deepsearch import (
    graph,
    extract_content,
    MULTIHOP_QA_INSTRUCTION
)

load_dotenv()

APPEND_ANSWER_LOCK = threading.Lock()

reranker_ip = os.getenv("RERANKER_SERVER_HOST_IP")
reranker_port = os.getenv("RERANKER_SERVER_PORT")
openai_api_key = os.getenv("LAMBDA_API_KEY")

if openai_api_key:
    model_id = "deepseek-r1-671b"
else:
    model_id = "gemini-2.5-flash-preview-04-17"

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
        default=["./evals/datasets/frames_test_set.csv"],
        help="List of evaluation task paths",
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=8,
        help="The number of processes to run in parallel",
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
    jsonl_file = Path(jsonl_file)
    jsonl_file.parent.mkdir(parents=True, exist_ok=True)
    with APPEND_ANSWER_LOCK, open(jsonl_file, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")
    assert os.path.exists(jsonl_file), "File not found!"


def run_with_timeout(func, timeout):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            return "Timed Out"

async def answer_single_question(example, answers_file):
    augmented_question = example["question"]
    prompt = MULTIHOP_QA_INSTRUCTION.format(
        question=augmented_question)

    TIMEOUT_SECONDS = 300  # 5 minutes timeout

    async def get_agent_response():
        res = await graph.ainvoke({
        #res = await graph.ainvoke({
            "messages": [HumanMessage(prompt)],
            "current_iter": 0,
            "max_iter": 5,
            "search_query": "",
            "search_summary": "",
            "answer": "",
            "plan_goal": "",
            "plan_result": [],
            "plan_query_index": -1,
            "needs_replan": False,
            "previous_plan": [],
            "reflection": "",
            },
            {"recursion_limit": 40}
        )

        response = res["messages"][-1].content
        answer = extract_content(response, "answer")
        if answer is None:
            answer = "Failed without an answer!"
        return answer

    try:
        answer = await asyncio.wait_for(get_agent_response(), timeout=TIMEOUT_SECONDS)
        #answer = run_with_timeout(get_agent_response, TIMEOUT_SECONDS)
    except Exception as e:
        print("Error on ", augmented_question, e)
        answer = "Exception occurred"

    annotated_example = {
        "model_id": model_id,
        "original_question": example["question"],
        "answer": answer,
        "true_answer": example["true_answer"],
    }
    append_answer(annotated_example, answers_file)

def answer_sync(example, file_name):
        return asyncio.run(answer_single_question(example, file_name))

def answer_questions(
    eval_ds,
    output_dir: str = "output",
    parallel_workers: int = 32,
):
    # Create directory structure: output/model_id/reranker/task
    model_dir = model_id.replace('/', '__')
    
    for task in eval_ds:
        task_dir = os.path.join(output_dir, model_id, reranker, task)
        os.makedirs(task_dir, exist_ok=True)
        
        file_name = f"{task_dir}/{model_id}__{reranker}__{task}.jsonl"
        print(f"Starting processing and writing output to '{file_name}'")
        answered_questions = []
        if os.path.exists(file_name):
            with open(file_name, "r") as f:
                for line in f:
                    answered_questions.append(json.loads(line)["original_question"])
        examples_todo = [example for example in eval_ds[task] if example["question"] not in answered_questions]
        print(f"Launching {parallel_workers} parallel workers.")

        with ThreadPoolExecutor(max_workers=parallel_workers) as exe:
            futures = [
                exe.submit(answer_sync, example, file_name) 
                for example in examples_todo
            ]
            for f in tqdm(as_completed(futures), total=len(examples_todo), desc="Processing tasks"):
                f.result()

        print("All tasks processed.")


if __name__ == "__main__":
    args = parse_arguments()

    eval_ds = load_eval_dataset(args.eval_tasks)
    answer_questions(
        eval_ds,
        parallel_workers=args.parallel_workers,
    )
