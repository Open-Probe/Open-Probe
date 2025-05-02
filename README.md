# 🔍 OpenDeepSearch - LangGraph Implementation

This document describes the LangGraph-based implementation of OpenDeepSearch, focusing on its agent structure, tools, and how to run the associated Gradio demo.

## Overview

This version utilizes LangChain's LangGraph framework to provide a structured and flexible agent architecture for performing deep web searches. It differs from the SmolAgent implementation in its agent logic and tool definitions.

**Key LangGraph Components:**

*   **Agent:** `src/opendeepsearch/lg_agent.py`
*   **Tools:** `src/opendeepsearch/lg_tools.py`, `src/opendeepsearch/wolfram_lg_tool.py`

## Installation

1.  Clone the repository (if you haven't already).
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    # Or using uv:
    # uv pip install -r requirements.txt
    ```

## Setup

1.  **Create Environment File:**
    Copy the `.env.example` file to `.env`:
    ```bash
    cp .env.example .env
    ```
2.  **Add API Keys:**
    Edit the `.env` file and add your necessary API keys. At a minimum, you'll likely need:
    *   `OPENROUTER_API_KEY` (or keys for your specific LLM provider like `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.)
    *   `SERPER_API_KEY` (if using Serper for search)
    *   `JINA_API_KEY` (if using Jina for reranking)
    *   `WOLFRAM_ALPHA_APP_ID` (if using the WolframAlpha tool)

    Configure other variables like `SEARXNG_INSTANCE_URL` if using SearXNG instead of Serper.

## Running the LangGraph Gradio Demo

To run the web interface specifically for the LangGraph implementation:

```bash
python lg_gradio_demo.py
```

This command launches a Gradio application using the agent and tools defined in `src/opendeepsearch/lg_agent.py` and `src/opendeepsearch/lg_tools.py`.

**Command Line Options for `lg_gradio_demo.py`:**

You can customize the demo's behavior using arguments:

```bash
python lg_gradio_demo.py \
  --model-name "provider/model-for-search" \
  --orchestrator-model "provider/model-for-agent" \
  --reranker "jina" \
  --search-provider "serper" \
  # Add other options like --searxng-instance if needed
```

*   `--model-name`: Specifies the LLM used within the search tool itself.
*   `--orchestrator-model`: Specifies the LLM used by the main LangGraph agent for reasoning and tool calls.
*   `--reranker`: Choose the reranking method (`jina` or `infinity`).
*   `--search-provider`: Select the search backend (`serper` or `searxng`).
*   *(Refer to `lg_gradio_demo.py` for all available options)*

## Alternative: SmolAgent Implementation

For comparison, the SmolAgent-based version can be run using:

```bash
python gradio_demo.py
```

This uses a different agent (`src/opendeepsearch/ods_agent.py`) and tool (`src/opendeepsearch/ods_tool.py`) structure.



