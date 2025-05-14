import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def web_search(query, api_key, provider="serper"):
    """Search for a given query on the web.

    Args:
        query: The search term to look up on the Web.
        api_key: The API key for the web search API. If None, will be loaded from environment.
        provider: Web search API provider.
    Returns:
        str: Web search results (snippets).
    """
    # If no API key provided, try to get from environment
    if api_key is None:
        api_key = os.getenv("WEB_SEARCH_API_KEY")

    if provider == "serpapi":
        params = {
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "google_domain": "google.com",
        }
        base_url = "https://serpapi.com/search.json"
        organic_key = "organic_results"
    else:
        params = {
            "q": query,
            "api_key": api_key,
        }
        base_url = "https://google.serper.dev/search"
        organic_key = "organic"

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        results = response.json()
    else:
        raise ValueError(response.json())

    web_snippets = []
    if organic_key in results:
        for idx, page in enumerate(results[organic_key]):
            date_published = ""
            if "date" in page:
                date_published = "\nDate published: " + page["date"]

            source = ""
            if "source" in page:
                source = "\nSource: " + page["source"]

            snippet = ""
            if "snippet" in page:
                snippet = "\n" + page["snippet"]

            redacted_version = f"{idx}. [{page['title']}]({page['link']}){date_published}{source}\n{snippet}"
            web_snippets.append(redacted_version)

    return "## Search Results\n" + "\n\n".join(web_snippets)
