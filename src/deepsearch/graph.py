import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langgraph.graph import START, END, StateGraph

from state import AgentState
from prompt import REACT_SYSTEM_PROMPT, SUMMARY_SYSTEM_PROMPT
from utils import extract_search_query, extract_answer, extract_content
from web_search import web_search


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


def search(state: AgentState):
    """Perform the actual web search and summarize the search result.

    Args:
        state: The current state of the agentic flow.

    Returns:
        dict: A dictionary containing the latest message and updated state.
    """
    search_result = web_search(state["search_query"], WEB_SEARCH_API_KEY)

    # Summary Messages: System + Human(Search result)
    summary_messages = [
        SystemMessage(SUMMARY_SYSTEM_PROMPT),
        HumanMessage(search_result)
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
