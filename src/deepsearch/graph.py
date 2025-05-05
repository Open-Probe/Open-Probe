import os

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph

from .prompt import REACT_SYSTEM_PROMPT, SUMMARY_SYSTEM_PROMPT
from .state import AgentState
from .utils import extract_answer, extract_content, extract_search_query
from .web_search.context_builder import build_context
from .web_search.serp_search import create_search_api
from .web_search.source_processor import SourceProcessor


def should_continue(state: AgentState):
    """Determine the next node based on the model's output.

    This function checks if the agent should continue its task.

    Args:
        state: The current state of the agentic flow.

    Returns:
        str: The name of the next node to call (END or "search").
    """
    # print("route_model_output", state)
    if state["current_iter"] == state["max_iter"] or \
       state["answer"] is not None:
        return END
    return "search"


def reason(state: AgentState):
    """Use ReAct reasoning framework to find the answer to the query.

    Args:
        state: The current state of the agentic flow.

    Returns:
        dict: A dictionary containing the latest message and updated state.
    """
    # print("call_model", state)

    # Messages: System + Human(Question) + multiple of [Thought, Action(Search), Observation(Search result)] steps
    messages = [SystemMessage(REACT_SYSTEM_PROMPT)] + state["messages"]

    ai_message = MODEL.invoke(messages, stop=["<observation>", "</answer>"])
    ai_message.content = ai_message.content.strip()

    if "<answer>" in ai_message.content:
        ai_message.content += "</answer>"
        # TODO: handle exception
        state["answer"] = extract_answer(ai_message.content)
    else:
        content = extract_content(ai_message.content, "action")
        state["search_query"] = extract_search_query(content)

    # Messages: System + prev_round + Thought + Action(Search)
    return {"messages": [ai_message], "answer": state["answer"], "search_query": state["search_query"]}


async def search(state: AgentState):
    """Perform the actual web search and summarize the search result.

    Args:
        state: The current state of the agentic flow.

    Returns:
        dict: A dictionary containing the latest message and updated state.
    """
    query = state["search_query"]
    serp_search_client = create_search_api(
        search_provider="serper",
        serper_api_key=WEB_SEARCH_API_KEY
    )

    sources = serp_search_client.get_sources(query)
    source_processor = SourceProcessor(reranker='jina')

    max_sources = 2
    processed_sources = await source_processor.process_sources(
        sources,
        max_sources,
        query,
        pro_mode=True
    )

    context = build_context(processed_sources)

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


WEB_SEARCH_API_KEY = os.environ["WEB_SEARCH_API_KEY"]
MODEL = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001")

builder = StateGraph(AgentState)
builder.add_node("reason", reason)
builder.add_node("search", search)

builder.add_edge(START, "reason")
builder.add_conditional_edges(
    "reason",
    should_continue,
)
builder.add_edge("search", "reason")

graph = builder.compile()
