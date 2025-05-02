from typing import Optional, Literal, Dict, Any
from langchain_core.tools import BaseTool, tool
from opendeepsearch.lg_agent import OpenDeepSearchAgentLanggraph

class OpenDeepSearchToolLanggraph(BaseTool):
    name: str = "web_search"
    description: str = """
    Performs web search based on your query (think a Google search) then returns the final answer that is processed by an llm."""
    inputs: Dict[str, Any] = {
        "query": {
            "type": "string",
            "description": "The search query to perform",
        },
    }
    output_type: str = "string"
    
    # Add missing Pydantic fields
    search_model_name: Optional[str] = None
    reranker: str = "jina"
    search_provider: Literal["serper", "searxng"] = "serper"
    serper_api_key: Optional[str] = None
    searxng_instance_url: Optional[str] = None
    searxng_api_key: Optional[str] = None
    search_tool: Optional[Any] = None

    def __init__(
        self,
        model_name: Optional[str] = None,
        reranker: str = "jina",
        search_provider: Literal["serper", "searxng"] = "serper",
        serper_api_key: Optional[str] = None,
        searxng_instance_url: Optional[str] = None,
        searxng_api_key: Optional[str] = None
    ):
        super().__init__()
        self.search_model_name = model_name
        self.reranker = reranker
        self.search_provider = search_provider
        self.serper_api_key = serper_api_key
        self.searxng_instance_url = searxng_instance_url
        self.searxng_api_key = searxng_api_key
        self.search_tool = None
        self._setup()

    def _setup(self):
        """Initialize the OpenDeepSearchAgent."""
        self.search_tool = OpenDeepSearchAgentLanggraph(
            self.search_model_name,
            reranker=self.reranker,
            search_provider=self.search_provider,
            serper_api_key=self.serper_api_key,
            searxng_instance_url=self.searxng_instance_url,
            searxng_api_key=self.searxng_api_key
        )

    def _run(self, query: str) -> str:
        """Execute the search tool.
        
        Args:
            query: The search query string
            
        Returns:
            The processed answer from the search
        """
        if not self.search_tool:
            self._setup()
        
        answer = self.search_tool.ask_sync(query, max_sources=2, pro_mode=True)
        return answer

# # Alternative implementation using the @tool decorator
# @tool
# def web_search(query: str, 
#                model_name: Optional[str] = None,
#                reranker: str = "jina", 
#                search_provider: str = "serper",
#                serper_api_key: Optional[str] = None,
#                searxng_instance_url: Optional[str] = None,
#                searxng_api_key: Optional[str] = None) -> str:
#     """
#     Performs web search based on your query (think a Google search) then returns the final answer that is processed by an llm.
    
#     Args:
#         query: The search query to perform
#         model_name: The model name to use for processing search results
#         reranker: The reranker to use (jina or infinity)
#         search_provider: The search provider to use (serper or searxng)
#         serper_api_key: The Serper API key
#         searxng_instance_url: The SearXNG instance URL
#         searxng_api_key: The SearXNG API key
        
#     Returns:
#         The processed answer from the search
#     """
#     # Create a transient agent for this request
#     search_tool = OpenDeepSearchAgentLanggraph(
#         model_name,
#         reranker=reranker,
#         search_provider=search_provider,
#         serper_api_key=serper_api_key,
#         searxng_instance_url=searxng_instance_url,
#         searxng_api_key=searxng_api_key
#     )
    
#     answer = search_tool.ask_sync(query, max_sources=2, pro_mode=True)
#     return answer
