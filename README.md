# AgentX OpenProbe (WIP)

## 🚀 Getting Started  

### 1. Install Dependencies  
Ensure you have Python installed, and then run:
```bash  
pip install -r requirements.txt  
```

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