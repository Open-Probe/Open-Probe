# AgentX OpenProbe

AgentX OpenProbe is a deep search system built using the LangChain and LangGraph frameworks. It's designed to perform comprehensive web searches and process the results for AI agents.

## 🚀 Getting Started  

### 1. Install Dependencies  
Ensure you have Python installed, and then run:
```bash  
pip install -r requirements.txt  
```

### 2. Install the Package
```bash
pip install -e .
```

### 3. Set Up API Keys
Set API keys as environment variables:
```bash
# Google Gemini API key
export GOOGLE_API_KEY=your_api_key

# Serper.dev API key for web search
export WEB_SEARCH_API_KEY=your_api_key

# Jina API key for reranking
export JINA_API_KEY=your_api_key
```

## Features

### Deep Search with Web Integration
- Comprehensive web search using Serper.dev
- Content extraction and processing
- Result reranking with Jina
- Context building for LLM consumption

### Advanced Features
- **Caching System**: Cache search results to avoid redundant API calls
- **Robust Error Handling**: With exponential backoff retry mechanism
- **Configurable Pipeline**: Easily adjust search parameters
- **Command-line Interface**: Use the system directly from the terminal
- **Interactive Mode**: Run queries in an interactive session

## Usage

### Command-line Interface

The system provides a convenient command-line interface:

```bash
# Run a single search query
python deepsearch.py search "your query here"

# Run in interactive mode
python deepsearch.py search --interactive

# Run with verbose output
python deepsearch.py search --verbose "your query here"

# Set maximum iterations
python deepsearch.py search --max-iterations 3 "your query here"
```

### Configuration Management

View and modify system configuration:

```bash
# Show current configuration
python deepsearch.py config --show

# Set configuration values
python deepsearch.py config --set max_sources=5 verbose=true

# Reset to default configuration
python deepsearch.py config --reset
```

### Test Script

For quick testing:

```bash
python test_deepsearch.py "your query here"
```

## Configuration Options

The system can be configured with the following options:

| Category | Option | Description | Default |
|----------|--------|-------------|---------|
| Search | max_sources | Maximum number of sources to process | 3 |
| Search | max_iterations | Maximum search iterations | 5 |
| Search | web_search_provider | Search provider to use | serper |
| Search | reranker | Reranking algorithm | jina |
| Search | pro_mode | Enable advanced processing | true |
| Cache | cache_enabled | Enable result caching | true |
| Cache | cache_max_age_days | Cache expiration in days | 7 |
| Retry | retry_max_attempts | Maximum retry attempts | 3 |
| Retry | retry_initial_delay | Initial delay between retries | 1.0 |
| Model | model_name | LLM model to use | gemini-2.5-pro-preview-05-06 |

## Development

For more detailed information about specific components:

- [Web Search Module Documentation](src/deepsearch/web_search/README.md)

## To-Dos

### Deep Search
- Add deeper web search from OpenDeepSearch

## License

See [LICENSE](LICENSE) file for details.