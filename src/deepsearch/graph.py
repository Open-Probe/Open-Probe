import os
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from .prompt import REACT_SYSTEM_PROMPT, SUMMARY_SYSTEM_PROMPT, PLANNING_INSTRUCTION
from .state import AgentState
from .utils import extract_content, extract_plan_result
from .web_search.context_builder import build_context
from .web_search.serp_search import create_search_api
from .web_search.source_processor import SourceProcessor


def master(state: AgentState) -> Command[Literal["plan", "search", END]]:
    messages = [SystemMessage(REACT_SYSTEM_PROMPT)] + state["messages"]

    ai_message = MODEL.invoke(messages, stop=["</plan>", "</search_query>", "</answer>"])
    ai_message.content = ai_message.content.strip()

    if "<plan>" in ai_message.content:
        ai_message.content += "</plan>"
        state["plan_goal"] = extract_content(ai_message.content, "plan")
        return Command(
            goto="plan",
            update={"messages": [ai_message], "plan_goal": state["plan_goal"]}
        )
    elif "<search_query>" in ai_message.content:
        ai_message.content += "</search_query>"
        state["search_query"] = extract_content(ai_message.content, "search_query")
        return Command(
            goto="search",
            update={"messages": [ai_message], "search_query": state["search_query"]}
        )
    elif "<answer>" in ai_message.content:
        ai_message.content += "</answer>"
        # TODO: handle exception
        state["answer"] = extract_content(ai_message.content, "answer")
        return Command(
            goto=END,
            update={"messages": [ai_message], "answer": state["answer"]}
        )


def plan(state: AgentState) -> Command[Literal["master"]]:
    plan_goal = state["plan_goal"]
    message = [HumanMessage(PLANNING_INSTRUCTION.format(plan_goal))]
    ai_message = MODEL.invoke(message)

    plan_result = ai_message.content.strip()
    # TODO: extract json string
    plan_result = extract_plan_result(plan_result)
    state["plan_result"] = plan_result
    ai_message = AIMessage(
        f"<plan_result>{plan_result}</plan_result>"
    )
    return Command(
        goto="master",
        update={"messages": [ai_message], "plan_result": state["plan_result"]}
    )


async def search(state: AgentState) -> Command[Literal["master"]]:
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

    ai_message = AIMessage(
        f"<search_result>{summary_ai_message.content}</search_result>")
    return Command(
        goto="master",
        update={"messages": [ai_message], "search_summary": state["search_summary"], "current_iter": state["current_iter"] + 1}
    )


WEB_SEARCH_API_KEY = os.environ["WEB_SEARCH_API_KEY"]
MODEL = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001")

builder = StateGraph(AgentState)
builder.add_node("reason", master)
builder.add_node("plan", plan)
builder.add_node("search", search)

builder.add_edge(START, "master")

graph = builder.compile()
