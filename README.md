# AgentX OpenProbe (WIP)

## 🚀 Getting Started  

### 1. Install Dependencies  
Ensure you have Python installed, and then run:
```bash  
pip install -r requirements.txt  
```

## Features

### DeepSearch
The DeepSearch system is designed to perform multi-step web searches with intelligent planning and replanning capabilities:

- **Automated Planning**: Breaks down complex queries into multiple search steps
- **Adaptive Replanning**: Analyzes search results and revises the search strategy when initial plans are insufficient
- **Reflection**: Provides reasoning about why previous plans failed and how to improve them
- **Web Search Integration**: Seamlessly integrates with search APIs to gather information

#### How it Works
1. The system analyzes the user's question
2. It creates a search plan with multiple sub-queries
3. It executes searches based on the plan
4. If results are insufficient, it can replan with improved queries
5. Finally, it synthesizes all information into a comprehensive answer

## To-Dos

### Deep Search
- Add deeper web search from OpenDeepSearch

## How to Run

### Set Up API Keys
Set API keys to environment variable
- Google Gemini:  
    ```bash  
    export GOOGLE_API_KEY=your_api_key
    ```

- Serper.dev:
    ```bash 
    export WEB_SEARCH_API_KEY=your_api_key
    ```

- Jina:
    ```bash 
    export JINA_API_KEY=your_api_key
    ```

### Installation
```bash
cd openprobe_dev
pip install -e .
```

### Run
```bash
python test_deepsearch.py
```