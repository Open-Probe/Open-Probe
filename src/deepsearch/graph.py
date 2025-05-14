import os
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from .prompt import REACT_SYSTEM_PROMPT, SUMMARY_SYSTEM_PROMPT
from .state import AgentState
from .utils import extract_answer, extract_content, extract_search_query, SearchCache, retry_with_exponential_backoff
from .web_search.context_builder import build_context
from .web_search.serp_search import create_search_api
from .web_search.source_processor import SourceProcessor
from .config import config

# Initialize search cache
search_cache = SearchCache(
    max_age_days=config.get("cache_max_age_days")
) if config.get("cache_enabled") else None

# Initialize the language model
MODEL = ChatGoogleGenerativeAI(
    model=config.get("model_name"),
    google_api_key=config.get("google_api_key")
)

def should_continue(state: AgentState):
    """Determine the next node based on the model's output.

    This function checks if the agent should continue its task.

    Args:
        state: The current state of the agentic flow.

    Returns:
        str: The name of the next node to call (END or "search").
    """
    if config.get("verbose"):
        print(f"Current iteration: {state['current_iter']}/{state['max_iter']}")
        print(f"Answer found: {'Yes' if state['answer'] is not None else 'No'}")
    
    if state["current_iter"] == state["max_iter"] or state["answer"] is not None:
        return END
    return "search"


def reason(state: AgentState):
    """Use ReAct reasoning framework to find the answer to the query.

    Args:
        state: The current state of the agentic flow.

    Returns:
        dict: A dictionary containing the latest message and updated state.
    """
    if config.get("verbose"):
        print("Reasoning about the query...")
    
    # Messages: System + Human(Question) + multiple of [Thought, Action(Search), Observation(Search result)] steps
    messages = [SystemMessage(REACT_SYSTEM_PROMPT)] + state["messages"]

    ai_message = MODEL.invoke(messages, stop=["<observation>", "</answer>"])
    ai_message.content = ai_message.content.strip()

    if "<answer>" in ai_message.content:
        ai_message.content += "</answer>"
        try:
            state["answer"] = extract_answer(ai_message.content)
            if config.get("verbose"):
                print(f"Answer found: {state['answer']}")
        except Exception as e:
            print(f"Error extracting answer: {e}")
    else:
        try:
            content = extract_content(ai_message.content, "action")
            state["search_query"] = extract_search_query(content)
            if config.get("verbose"):
                print(f"Search query: {state['search_query']}")
        except Exception as e:
            print(f"Error extracting search query: {e}")
            # Use a fallback search query if extraction fails
            state["search_query"] = "error extracting search query"
    
    # Messages: System + prev_round + Thought + Action(Search)
    return {"messages": [ai_message], "answer": state["answer"], "search_query": state["search_query"]}


@retry_with_exponential_backoff(
    initial_delay=config.get("retry_initial_delay"),
    exponential_base=config.get("retry_base"),
    jitter=config.get("retry_jitter"),
    max_retries=config.get("retry_max_attempts")
)
async def _perform_search(query, pro_mode=True):
    """Internal function to perform the actual search with retry logic.
    
    Args:
        query: The search query
        pro_mode: Whether to use pro mode for processing sources
        
    Returns:
        The processed sources and context
    """
    serp_search_client = create_search_api(
        search_provider=config.get("web_search_provider"),
        serper_api_key=config.get("web_search_api_key")
    )

    sources = serp_search_client.get_sources(query)
    source_processor = SourceProcessor(reranker=config.get("reranker"))

    processed_sources = await source_processor.process_sources(
        sources,
        config.get("max_sources"),
        query,
        pro_mode=pro_mode
    )

    context = build_context(processed_sources)
    return processed_sources, context


async def search(state: AgentState):
    """Perform the actual web search and summarize the search result.

    Args:
        state: The current state of the agentic flow.

    Returns:
        dict: A dictionary containing the latest message and updated state.
    """
    query = state["search_query"]
    
    if config.get("verbose"):
        print(f"Searching for: {query}")
    
    # Check cache if enabled
    cached_result = None
    if search_cache:
        cached_result = search_cache.get(query)
    
    if cached_result:
        if config.get("verbose"):
            print(f"Using cached search results for '{query}'")
        context = cached_result.get("context")
    else:
        try:
            processed_sources, context = await _perform_search(
                query, 
                pro_mode=config.get("pro_mode")
            )
            
            # Cache results if enabled - only store the context, not the source objects
            if search_cache:
                search_cache.set(query, {
                    "context": context,
                    # Don't store the sources objects directly as they may not be serializable
                    # Instead, just store the fact that we have sources
                    "has_sources": True
                })
        except Exception as e:
            print(f"Search failed: {e}")
            # Return a message about the search failure
            context = f"Search failed for '{query}'. Error: {str(e)}"
    
    # Summary Messages: System + Human(Search result)
    summary_messages = [
        SystemMessage(SUMMARY_SYSTEM_PROMPT),
        HumanMessage(context)
    ]
    summary_ai_message = MODEL.invoke(summary_messages)
    summary_ai_message.content = summary_ai_message.content.strip()
    state["search_summary"] = summary_ai_message.content

    # Messages: System + Human(Question) + Thought + Action(Search) + Observation(Search result)
    ai_message = AIMessage(
        f"<observation>{summary_ai_message.content}</observation>")
    return {"messages": [ai_message], "search_summary": state["search_summary"], "current_iter": state["current_iter"] + 1}


def create_graph(max_iterations=None):
    """Create a new graph instance with optional configuration.
    
    Args:
        max_iterations: Override the maximum number of iterations
        
    Returns:
        A compiled graph instance
    """
    builder = StateGraph(AgentState)
    builder.add_node("reason", reason)
    builder.add_node("search", search)

    builder.add_edge(START, "reason")
    builder.add_conditional_edges(
        "reason",
        should_continue,
    )
    builder.add_edge("search", "reason")

    graph_instance = builder.compile()
    
    if config.get("verbose"):
        print("Graph created successfully")
    
    return graph_instance


# Default graph instance
graph = create_graph()
