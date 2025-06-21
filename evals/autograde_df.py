import os, json
import requests
import pandas as pd
import litellm
import argparse
from mistralai import Mistral
from huggingface_hub import InferenceClient
from evals.grader_prompts import GRADER_TEMPLATE
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

def grade_row(provider, row_data):
    gaudi = os.getenv("USE_GAUDI")
    idx, row = row_data
    question = row['original_question']
    predicted_answer = row['answer']
    gold_answer = row['true_answer']
    
    input_prompt = GRADER_TEMPLATE.format(
        question=question,
        predicted_answer=predicted_answer,
        target=gold_answer
    )
    
    try:
        if provider=="gaudi":
            messages=[{"role": "user", "content": input_prompt}]
            # Define the URL and headers
            url = "http://100.83.55.207:8010/v1/chat/completions"
            headers = {
                "Content-Type": "application/json"
            }

            # Define the payload
            data = {
                "model": "meta-llama/Meta-Llama-3-8B-Instruct",
                "messages": messages,
                "temperature": 0.0
            }

            # Make the POST request
            response = requests.post(url, headers=headers, data=json.dumps(data))
            data = response.json()
            print("data=", data)
            output = data['choices'][0]['message']['content']
        elif provider=="huggingface":
            client = InferenceClient(
                provider="together",
                api_key=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
                bill_to="OpenProbe"
            )
            completion = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1", 
                messages=[{"role": "user", "content": input_prompt}],
                max_tokens=500
            )

            print(f"message={completion.choices[0].message}")            
            output = completion.choices[0].message['content']
            print(f"output={output}")
        elif provider=="mistral":
            api_key = os.environ["MISTRAL_API_KEY"]
            client = Mistral(api_key=api_key)
    
            model = "mistral-large-2411"

            response = client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": input_prompt}],
                temperature=0,
                top_p=1,
            )

            print(response.choices[0].message.content)


            print(f"response={response.choices[0].message.content}")
            output = response.choices[0].message.content.strip()
            print(f"output={output}")
        return idx, output
    except Exception as e:
        print(f"Error processing row {idx}: {e}")
        return idx, "Error"

def autograde_df(df_path, provider, num_cpus=4):
    # Read the dataframe
    df = pd.read_json(df_path, lines=True)
    
    # Prepare data for parallel processing
    row_data = list(df.iterrows())
    
    # Use specified number of CPU cores
    n_processes = max(1, min(num_cpus, cpu_count()))
    print(f"Using {n_processes} processes")
    
    # Create process pool and process rows in parallel
    with Pool(n_processes) as pool:
        tasks = [(provider, row) for row in row_data]
        # Use tqdm for progress bar
        results = list(tqdm(
            pool.starmap(grade_row, tasks),
            total=len(row_data),
            desc="Grading"
        ))
    
    # Sort results by index and extract grades
    results.sort(key=lambda x: x[0])
    final_grades = [grade for _, grade in results]
    
    # Add the grades as a new column
    df['final_grade'] = final_grades
    
    # Save the updated dataframe back to the same file
    df.to_json(df_path, orient='records', lines=True)
    print("Grading completed and results saved!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Auto-grade answers in a DataFrame')
    parser.add_argument('df_path', type=str, help='Path to the DataFrame JSON file')
    parser.add_argument('--provider', type=str, default='mistral', help='Name of provider')
    parser.add_argument('--num_cpus', type=int, default=4, help='Number of CPU cores to use')
    
    args = parser.parse_args()
    autograde_df(args.df_path, args.provider, args.num_cpus)
