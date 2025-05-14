# DeepSearch Web Search Module

This directory contains the core components of the DeepSearch web search system, which provides comprehensive search capabilities with advanced features like result reranking, content processing, and caching.

## Architecture

The web search module is designed as a pipeline with several specialized components:

1. **Search Engine Integration** (`serp_search.py`): Interfaces with search engine APIs (currently Serper.dev) to fetch search results.

2. **Web Scraping** (`crawl4ai_scraper.py`): Extracts content from web pages found in search results.

3. **Content Processing** (`source_processor.py`): Processes and cleans the scraped content.

4. **Text Chunking** (`chunker.py`): Breaks down large content into manageable chunks.

5. **Result Ranking** (`jina_reranker.py`, `base_reranker.py`): Reranks search results based on relevance to the query.

6. **Context Building** (`context_builder.py`): Builds a comprehensive context from the processed results.

7. **Main Interface** (`web_search.py`): Coordinates all components into a cohesive search pipeline.

## Features

### Caching System

DeepSearch includes a robust caching system that stores search results to avoid redundant API calls:

- **Location**: Cache files are stored in `~/.openprobe/cache/` by default
- **Format**: Each cache entry is a JSON file with search results
- **Expiration**: Cache entries expire after 7 days by default (configurable)
- **Identification**: Cache keys are generated using MD5 hashes of search queries

To configure caching:

```python
# Enable/disable caching
config.set("cache_enabled", True)

# Set cache expiration in days
config.set("cache_max_age_days", 7)
```

### Error Handling and Retries

The system includes robust error handling with an exponential backoff retry mechanism:

- Automatically retries failed API calls
- Configurable retry parameters (attempts, delay, jitter)
- Graceful error reporting

Configuration options:

```python
# Maximum retry attempts
config.set("retry_max_attempts", 3)

# Initial delay between retries (seconds)
config.set("retry_initial_delay", 1.0)

# Exponential base for backoff
config.set("retry_base", 2.0)

# Enable jitter to prevent thundering herd
config.set("retry_jitter", True)
```

### Configurable Search Parameters

The search process is highly configurable:

- **Max Sources**: Control how many sources to process (`max_sources`)
- **Search Provider**: Select the search engine provider (`web_search_provider`)
- **Reranker**: Choose the reranking algorithm (`reranker`)
- **Pro Mode**: Enable advanced processing features (`pro_mode`)

## Usage

### Basic Usage

```python
from deepsearch.web_search.serp_search import create_search_api
from deepsearch.web_search.source_processor import SourceProcessor
from deepsearch.web_search.context_builder import build_context

# Create search client
search_client = create_search_api(
    search_provider="serper",
    serper_api_key="your_api_key"
)

# Get sources
sources = search_client.get_sources("your search query")

# Process sources
source_processor = SourceProcessor(reranker='jina')
processed_sources = await source_processor.process_sources(
    sources,
    max_sources=3,
    query="your search query",
    pro_mode=True
)

# Build context
context = build_context(processed_sources)
```

### Using the DeepSearch CLI

For a more convenient experience, use the CLI:

```bash
# Run a single search
python deepsearch.py search "your query here"

# Interactive mode
python deepsearch.py search --interactive

# Configure search parameters
python deepsearch.py config --set max_sources=5 verbose=true
```

## API Keys

The following API keys are required:

- **Web Search API Key**: For search engine access (Serper.dev)
- **Jina API Key**: For reranking (optional but recommended)

Set these as environment variables or in the configuration:

```bash
export WEB_SEARCH_API_KEY=your_api_key
export JINA_API_KEY=your_api_key
```

Or use configuration:

```python
config.set("web_search_api_key", "your_api_key")
config.set("jina_api_key", "your_api_key")
``` 