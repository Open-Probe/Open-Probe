import os, json
import requests
import pandas as pd
import litellm
import argparse
import logging
from datetime import datetime
from mistralai import Mistral
from huggingface_hub import InferenceClient
from evals.grader_prompts import GRADER_TEMPLATE
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

# Optional import for Gemini via LangChain provider wrapper
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:  # pragma: no cover
    ChatGoogleGenerativeAI = None
try:
    from langchain_core.messages import HumanMessage
except Exception:  # pragma: no cover
    HumanMessage = None

def setup_logging(log_level=logging.INFO):
    """Setup logging configuration with timestamp and formatting"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"autograde_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_filename}")
    return logger

def grade_row(provider, row_data):
    logger = logging.getLogger(__name__)
    gaudi = os.getenv("USE_GAUDI")
    idx, row = row_data
    question = row['original_question']
    predicted_answer = row['answer']
    gold_answer = row['true_answer']
    
    logger.info(f"Processing row {idx}: Question='{question[:100]}...'")
    logger.debug(f"Row {idx} details - Predicted: '{predicted_answer[:100]}...', Gold: '{gold_answer[:100]}...'")
    
    input_prompt = GRADER_TEMPLATE.format(
        question=question,
        predicted_answer=predicted_answer,
        target=gold_answer
    )
    
    try:
        if provider=="gaudi":
            logger.info(f"Row {idx}: Using Gaudi provider")
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

            logger.debug(f"Row {idx}: Making request to Gaudi API")
            # Make the POST request
            response = requests.post(url, headers=headers, data=json.dumps(data))
            data = response.json()
            logger.debug(f"Row {idx}: Gaudi API response: {data}")
            output = data['choices'][0]['message']['content']
            logger.info(f"Row {idx}: Gaudi grading completed successfully")
            
        elif provider=="huggingface":
            logger.info(f"Row {idx}: Using HuggingFace provider")
            client = InferenceClient(
                provider="together",
                api_key=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
                bill_to="OpenProbe"
            )
            logger.debug(f"Row {idx}: Making request to HuggingFace API")
            completion = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1", 
                messages=[{"role": "user", "content": input_prompt}],
                max_tokens=500
            )

            logger.debug(f"Row {idx}: HuggingFace API response: {completion.choices[0].message}")            
            output = completion.choices[0].message['content']
            logger.info(f"Row {idx}: HuggingFace grading completed successfully")
            
        elif provider=="mistral":
            logger.info(f"Row {idx}: Using Mistral provider")
            api_key = os.environ["MISTRAL_API_KEY"]
            client = Mistral(api_key=api_key)
    
            model = "mistral-large-2411"
            logger.debug(f"Row {idx}: Making request to Mistral API with model {model}")

            response = client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": input_prompt}],
                temperature=0,
                top_p=1,
            )

            logger.debug(f"Row {idx}: Mistral API response: {response.choices[0].message.content}")
            output = response.choices[0].message.content.strip()
            logger.info(f"Row {idx}: Mistral grading completed successfully")
            
        elif provider=="gemini":
            logger.info(f"Row {idx}: Using Gemini provider")
            if ChatGoogleGenerativeAI is None:
                raise ImportError("langchain-google-genai is not installed. Please install requirements.txt")
            google_api_key = os.environ.get("GOOGLE_API_KEY")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY is not set in environment")

            # Use a small fast model for grading; consistent deterministic behavior
            model_id = os.environ.get("GEMINI_GRADER_MODEL", "gemini-2.5-flash")
            logger.debug(f"Row {idx}: Using Gemini model: {model_id}")
            
            grader = ChatGoogleGenerativeAI(
                model=model_id,
                temperature=0.0,
                google_api_key=google_api_key,
            )

            logger.debug(f"Row {idx}: Making request to Gemini API")
            # Invoke with a plain prompt string
            resp = grader.invoke(input_prompt)
            # Convert to string content
            output = getattr(resp, "content", str(resp)).strip()
            logger.info(f"Row {idx}: Gemini grading completed successfully")
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
        logger.debug(f"Row {idx}: Raw output: '{output[:200]}...'")
        return idx, output
        
    except Exception as e:
        logger.error(f"Error processing row {idx}: {str(e)}", exc_info=True)
        return idx, "Error"

def autograde_df(df_path, provider, num_cpus=4):
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting autograde process")
    logger.info(f"Input file: {df_path}")
    logger.info(f"Provider: {provider}")
    logger.info(f"CPU cores: {num_cpus}")
    
    # Read the dataframe
    logger.info("Reading input DataFrame")
    try:
        df = pd.read_json(df_path, lines=True)
        logger.info(f"Successfully loaded DataFrame with {len(df)} rows")
        logger.debug(f"DataFrame columns: {list(df.columns)}")
    except Exception as e:
        logger.error(f"Failed to read DataFrame from {df_path}: {str(e)}", exc_info=True)
        raise
    
    # Prepare data for parallel processing
    row_data = list(df.iterrows())
    logger.info(f"Prepared {len(row_data)} rows for processing")
    
    # Use specified number of CPU cores
    n_processes = max(1, min(num_cpus, cpu_count()))
    logger.info(f"Using {n_processes} processes (requested: {num_cpus}, available: {cpu_count()})")
    
    # Create process pool and process rows in parallel
    logger.info("Starting parallel processing")
    start_time = datetime.now()
    
    with Pool(n_processes) as pool:
        tasks = [(provider, row) for row in row_data]
        logger.info(f"Created {len(tasks)} tasks for processing")
        
        # Use tqdm for progress bar
        results = list(tqdm(
            pool.starmap(grade_row, tasks),
            total=len(row_data),
            desc="Grading"
        ))
    
    end_time = datetime.now()
    processing_time = end_time - start_time
    logger.info(f"Parallel processing completed in {processing_time}")
    
    # Sort results by index and extract grades
    logger.info("Processing results")
    results.sort(key=lambda x: x[0])
    final_grades = [grade for _, grade in results]
    
    # Count successful vs error grades
    successful_grades = sum(1 for grade in final_grades if grade != "Error")
    error_grades = sum(1 for grade in final_grades if grade == "Error")
    logger.info(f"Grading results: {successful_grades} successful, {error_grades} errors")
    
    # Add the grades as a new column
    df['final_grade'] = final_grades
    logger.info("Added final_grade column to DataFrame")
    
    # Save the updated dataframe back to the same file
    logger.info(f"Saving results to {df_path}")
    try:
        df.to_json(df_path, orient='records', lines=True)
        logger.info("Grading completed and results saved successfully!")
    except Exception as e:
        logger.error(f"Failed to save results: {str(e)}", exc_info=True)
        raise
    
    # Log summary statistics
    grade_counts = df['final_grade'].value_counts()
    logger.info("Final grade distribution:")
    for grade, count in grade_counts.items():
        logger.info(f"  {grade}: {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Auto-grade answers in a DataFrame')
    parser.add_argument('--df_path', type=str, help='Path to the DataFrame JSON file')
    parser.add_argument('--provider', type=str, default='mistral', help='Name of provider')
    parser.add_argument('--num_cpus', type=int, default=4, help='Number of CPU cores to use')
    parser.add_argument('--log-level', type=str, default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = getattr(logging, args.log_level.upper())
    logger = setup_logging(log_level)
    
    logger.info("=" * 50)
    logger.info("AUTOGRADE PROCESS STARTED")
    logger.info("=" * 50)
    
    try:
        autograde_df(args.df_path, args.provider, args.num_cpus)
        logger.info("=" * 50)
        logger.info("AUTOGRADE PROCESS COMPLETED SUCCESSFULLY")
        logger.info("=" * 50)
    except Exception as e:
        logger.error("=" * 50)
        logger.error("AUTOGRADE PROCESS FAILED")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 50)
        raise
