# OpenProbe - Advanced Agent-Based Search System

OpenProbe is an advanced agent-based search system that performs deep web searches to answer complex questions. It uses a graph-based approach with LangGraph to orchestrate different components and deliver comprehensive answers.

## 🏗️ Architecture
<img width="1084" height="490" alt="image" src="https://github.com/user-attachments/assets/d8636fd7-3add-4c10-aa01-044a4e90781f" />

## ✨ Features

- **Deep Web Search**: Multi-step search process with intelligent planning and execution.
- **Automated Planning**: Breaks down complex queries into multiple sub-queries for efficient searching.
- **Adaptive Replanning**: Revises search strategies when initial plans fall short (default up to 1 replan; configurable via CLI).
- **Reflection**: Explains why previous plans failed and how they were improved.
- **Web Search Integration**: Seamlessly integrates with multiple search APIs for information retrieval.
- **Intelligent Reranking**: Jina-powered result reranking with optional local reranker support.
- **Query Rewriting**: Automatically rephrases tool inputs into better search queries.
- **Code Execution Tool**: Executes generated Python code in a local REPL to compute answers when needed.
- **Evaluation Framework**: Built-in evaluation system for testing search quality.
- **CLI Interface**: Command-line tool for easy interaction.
- **Caching System**: Persistent caching for improved performance.
- **Configuration Management**: Flexible configuration with persistent settings.

### Core Components

- **Search Engine**: Main orchestration system in `src/deepsearch/graph.py`
- **Web Search**: Search functionality in `src/deepsearch/web_search/`
- **State Management**: Agent state management in `src/deepsearch/state.py`
- **Evaluation System**: Testing framework in `evals/`
- **Configuration**: Settings management with persistent storage

### LangGraph Workflow

The system uses LangGraph to orchestrate the search process with these key nodes:

1. **Master Node**: Central decision-making component
2. **Plan Node**: Generates structured research plans
3. **Search Node**: Executes web searches and processes results
4. **Code Node**: Generates and executes Python when helpful
5. **Solve Node**: Synthesizes intermediate results into a final answer
6. **Replan Node**: Reflects and replans when results are insufficient

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- API keys for:
  - Google Gemini API (required)
  - Serper.dev API (for web search)
  - Jina API (for reranking)
  - Lambda/OpenAI-compatible API (optional; enable alternative models via `LAMBDA_API_KEY`)
- Optional local reranker service (set host/port env vars)

### Setup Steps

1. **Clone and Install Dependencies**
   ```bash
   git clone <repository-url>
   cd openprobe_dev
   pip install -r requirements.txt
   ```

2. **Development Installation**
   ```bash
   pip install -e .
   ```

3. **Set Up API Keys**
   
   Set environment variables:
   ```bash
   # Google Gemini API key for LLM (default provider)
   export GOOGLE_API_KEY=your_api_key
   
   # Serper.dev API key for web search
   export WEB_SEARCH_API_KEY=your_api_key
   
   # Jina API key for reranking
   export JINA_API_KEY=your_api_key

   # Optional: Use Lambda/OpenAI-compatible models via Lambda API
   export LAMBDA_API_KEY=your_api_key

   # Optional: Use a local reranker service instead of Jina
   export RERANKER_SERVER_HOST_IP=127.0.0.1
   export RERANKER_SERVER_PORT=8080
   ```
   
   Or create a `.env` file in the project root:
   ```env
   GOOGLE_API_KEY=your_api_key
   WEB_SEARCH_API_KEY=your_api_key
   JINA_API_KEY=your_api_key
   LAMBDA_API_KEY=your_api_key # optional
   RERANKER_SERVER_HOST_IP=127.0.0.1 # optional
   RERANKER_SERVER_PORT=8080        # optional
   ```

## 🚀 Quick Start

### Using the Test Script
```bash
python test_deepsearch.py
```

### Using the CLI

The CLI provides comprehensive interaction with the DeepSearch system:

```bash
# Run a direct search
python -m src.deepsearch.cli search "What are the latest developments in quantum computing?"

# Run with custom parameters
python -m src.deepsearch.cli search --max-replan 2 "Who won the most recent Olympic games?"

# Run in interactive mode
python -m src.deepsearch.cli search --interactive

# Show version information
python -m src.deepsearch.cli version
```

## ⚙️ Parameters

OpenProbe behavior is controlled via CLI flags and environment variables.

### CLI Flags

- `search --max-replan <int>`: Maximum replanning iterations (default: 1)
- `search --interactive` / `-i`: Run in interactive mode

### Environment Variables

- `GOOGLE_API_KEY`: Required for default Gemini models
- `WEB_SEARCH_API_KEY`: Required for Serper.dev search
- `JINA_API_KEY`: Required for Jina reranking (if not using local reranker)
- `LAMBDA_API_KEY` (optional): Use Lambda/OpenAI-compatible models instead of Gemini
- `RERANKER_SERVER_HOST_IP` and `RERANKER_SERVER_PORT` (optional): Use local reranker instead of Jina

## 🔍 How It Works

### Search Pipeline

1. **Query Analysis**: The system analyzes the user's question
2. **Plan Generation**: Creates a search plan with multiple sub-queries
3. **Search Execution**: Executes searches based on the plan using:
   - SERP Search via Serper.dev
   - Content extraction and processing
   - Intelligent reranking with Jina or a local reranker
4. **Result Processing**: Aggregates and processes search results
5. **Adaptive Replanning**: If results are insufficient, replans with improved queries (configurable via `--max-replan`)
6. **Answer Synthesis**: Synthesizes all information into a comprehensive answer

### Web Search Components

The web search system includes:

- **SERP Search**: Serper.dev API integration
- **Content Processing**: Web scraping and content cleaning
- **Chunking**: Text processing for manageable chunks
- **Reranking**: Jina-powered result enhancement (or local reranker if configured)
- **Context Building**: Comprehensive context aggregation
- **Caching**: Persistent result caching

## 📊 Evaluation System

OpenProbe includes a comprehensive evaluation framework in the `evals/` directory:

- **Accuracy Testing**: Automated accuracy evaluation
- **Dataset Management**: Test datasets for consistent evaluation
- **Grading System**: Automated grading of search results
- **Performance Metrics**: Detailed performance analysis

### Running Evaluations

```bash
# Run accuracy evaluations
python evals/accuracy.py

# Auto-grade results
python evals/autograde_df.py
```

## 🔧 System Limitations

- Maximum of 5 search attempts per session
- Default of 1 replanning attempt per query (configurable via `--max-replan`)
- After the replan limit is reached, the system must answer with available information
- Cache location: `~/.openprobe/cache/`
- Security note: The Code tool runs Python locally; review tasks before enabling code execution in untrusted environments.

## 📁 Project Structure

```
openprobe_dev/
├── src/deepsearch/           # Core DeepSearch module
│   ├── graph.py             # LangGraph workflow definition
│   ├── state.py             # State management
│   ├── prompt.py            # System prompts
│   ├── utils.py             # Utility functions
│   ├── cli.py               # Command-line interface
│   └── web_search/          # Web search components
│       ├── web_search.py    # Main search interface
│       ├── serp_search.py   # SERP API integration
│       ├── context_builder.py # Context aggregation
│       ├── jina_reranker.py # Result reranking
│       └── ...              # Other search components
├── evals/                   # Evaluation framework
├── data/                    # Data storage
├── test_deepsearch.py       # Test script
└── requirements.txt         # Dependencies
```

## 🔑 Key Dependencies

- **Google Gemini API**: Language model capabilities (default)
- **Lambda/OpenAI-compatible API**: Optional LLM provider when `LAMBDA_API_KEY` is set
- **Serper.dev**: Web search functionality
- **Jina**: Search result reranking (or local service)
- **LangGraph**: Workflow orchestration
- **LangChain**: LLM framework integration

## 📄 License

This project is licensed under the [Apache License Version 2.0](LICENSE). You are free to use, modify, and distribute this code, subject to the terms of the license.

---

## 🧩 References and Acknowledgements

This project builds upon and integrates ideas and code from various open-source projects, including:

* [LangChain](https://github.com/langchain-ai/langchain)
* [LangGraph](https://github.com/langchain-ai/langgraph)
* [LlamaIndex](https://github.com/jerryjliu/llama_index) — For data connectors and query engines.
* [Serper API](https://serper.dev/) — For web search capabilities.
* [Jina AI](https://github.com/jina-ai/jina) — For computing text embeddings.
* [Mistral](https://mistral.ai) — For LLM-based grading and evaluation.
* [LangGraph ReWOO implementation](https://langchain-ai.github.io/langgraph/tutorials/rewoo/rewoo) - Reference implemenation of ReWOO.
* [OpenDeepSearch](https://github.com/sentient-agi/OpenDeepSearch) - For implementing the web search tool and FRAMES evaluation.

Many thanks to these projects and their communities for making this work possible!

---

## 👥 Contributors

We'd like to thank the following people for their contributions to this project:

* **[Kuo-Hsin Tu](https://github.com/NTU-P04922004)** — Team Lead, Developer, Researcher
* **[Suryansh Singh Rawat](https://github.com/xsuryanshx)** — Developer
* **[Jean Yu](https://github.com/jeanyu-habana)** — Developer
* **[Ankit Basu](https://github.com/AnkitXP)** — Researcher

