# OpenProbe - Advanced Agent-Based Search System

OpenProbe is an agent-based search system that performs deep web searches to answer complex questions. It uses a web UI, a LangGraph-based agent orchestrator, and a comprehensive evaluation framework.

## 🏗️ Architecture
<img width="1084" height="490" alt="image" src="https://github.com/user-attachments/assets/d8636fd7-3add-4c10-aa01-044a4e90781f" />

## ✨ Features

- **Interactive Web UI**: A Next.js-based interface for interacting with the agent.
- **Deep Web Search**: Multi-step search process with automated planning and execution.
- **Adaptive Replanning**: Revises search strategies when initial plans fall short.
- **Reflection**: Explains why previous plans failed and how they were improved.
- **Intelligent Reranking**: Jina-powered result reranking with optional local reranker support.
- **Query Rewriting**: Rephrases tool inputs into better search queries.
- **Code Execution Tool**: Executes Python code in a local REPL to compute answers.
- **Multi-Model Support**: Natively supports Google Gemini and any OpenAI-compatible models via providers like Lambda.
- **Evaluation Framework**: Built-in system for testing search quality.
- **CLI Interface**: A command-line tool for direct interaction with the search agent.

### Core Components

- **Frontend**: A Next.js-based web interface in `frontend/`.
- **Backend**: A FastAPI server providing a REST API and WebSocket connection in `backend/`.
- **Search Engine**: The main agent orchestration system in `src/deepsearch/graph.py`.
- **Web Search**: Search functionality in `src/deepsearch/web_search/`.
- **State Management**: Agent state management in `src/deepsearch/state.py`.
- **Evaluation System**: Testing framework in `evals/`.

### LangGraph Workflow

The system uses LangGraph to orchestrate the search process:

1.  **Master Node**: Routes to other nodes based on the current state.
2.  **Plan Node**: Generates a structured research plan.
3.  **Search Node**: Executes web searches and summarizes findings.
4.  **Code Node**: Generates and executes Python code for computation.
5.  **Solve Node**: Synthesizes intermediate results into a final answer.
6.  **Replan Node**: Reflects on failures and generates a new plan.

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- Node.js and npm
- API keys for:
  - Google Gemini API or an OpenAI-compatible API key (e.g., for Lambda).
  - Serper.dev API (for web search)
  - Jina API (for reranking, if not using a local reranker)

### Setup Steps

1.  **Clone Repository**
    ```bash
    git clone <repository-url>
    cd openprobe_dev
    ```

2.  **Install Dependencies**
    ```bash
    # This single command installs all Python dependencies
    pip install -e .
    ```
    *Note: This project uses `uv` for faster dependency management, but `pip` is fully supported.*

3.  **Set Up API Keys**

    Create a `.env` file in the project root with your API keys:
    ```env
    # Google Gemini API key (default provider)
    GOOGLE_API_KEY=your_api_key

    # Serper.dev API key for web search
    WEB_SEARCH_API_KEY=your_api_key

    # Jina API key for reranking
    JINA_API_KEY=your_api_key

    # Optional: Use Lambda/OpenAI-compatible models
    LAMBDA_API_KEY=your_api_key
    ```

## 🚀 Running OpenProbe

To run the services manually:

1.  **Start the Backend**
    ```bash
    python backend/start_server.py
    ```

2.  **Start the Frontend**
    ```bash
    cd frontend
    # Install dependencies (only on first run)
    npm install
    # Run the UI
    npm run dev
    ```
Access the UI at **http://localhost:3000**.

### Using the CLI

The CLI provides direct access to the DeepSearch agent.

```bash
# The package should already be installed from the setup steps

# Run a search
python -m src.deepsearch.cli search "How many meters taller is the Burj Khalifa compared to the Empire State Building?"

# Run with more replanning attempts
python -m src.deepsearch.cli search --max-replan 2 "What year was the first Uber employee born?"

# Run in interactive mode
python -m src.deepsearch.cli search --interactive
```

## 🔧 System Limitations

- Default of 1 replanning attempt per query (configurable via `--max-replan`).
- The Code tool runs Python code locally, which has security implications. Use with caution.

## 📁 Project Structure

```
openprobe_dev/
├── backend/                # FastAPI backend for the UI
├── frontend/               # Next.js frontend for the UI
├── src/deepsearch/         # Core DeepSearch module
│   ├── graph.py            # LangGraph workflow definition
│   ├── state.py            # State management
│   ├── prompt.py           # System prompts
│   ├── cli.py              # Command-line interface
│   └── web_search/         # Web search components
├── evals/                  # Evaluation framework
├── pyproject.toml          # Python project configuration and dependencies
└── requirements.txt        # Python dependencies
```

## 🔑 Key Dependencies

- **FastAPI**: Backend server.
- **Next.js**: Frontend UI.
- **Google Gemini API**: Default LLM provider.
- **Lambda**: Supported provider for OpenAI-compatible models.
- **Serper.dev**: Web search functionality.
- **Jina**: Search result reranking.
- **LangGraph**: Workflow orchestration.

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
* [LangGraph ReWOO implementation](https://langchain-ai/langgraph/tutorials/rewoo/rewoo) - Reference implemenation of ReWOO.
* [OpenDeepSearch](https://github.com/sentient-agi/OpenDeepSearch) - For implementing the web search tool and FRAMES evaluation.

Many thanks to these projects and their communities for making this work possible!

---

## 👥 Contributors

We'd like to thank the following people for their contributions to this project:

* **[Suryansh Singh Rawat](https://github.com/xsuryanshx)** — Developer, Researcher
* **[Kuo-Hsin Tu](https://github.com/NTU-P04922004)** — Developer, Researcher
* **[Jean Yu](https://github.com/jeanyu-habana)** — Developer
* **[Ankit Basu](https://github.com/AnkitXP)** — Researcher
