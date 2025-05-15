import os
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from .prompt import MASTER_SYSTEM_PROMPT, SUMMARY_SYSTEM_PROMPT, PLANNING_INSTRUCTION, FIX_ANSWER_TAG_INSTRUCTION
from .state import AgentState
from .utils import extract_content, extract_plan_result, extract_last_json_block, remove_xml_blocks
from .web_search.context_builder import build_context
from .web_search.serp_search import create_search_api
from .web_search.source_processor import SourceProcessor


def master(state: AgentState) -> Command[Literal["plan", "search", END]]:
    messages = [SystemMessage(MASTER_SYSTEM_PROMPT)] + state["messages"]
    ai_message = MODEL.invoke(
        messages, stop=["</plan>", "</plan_result>", "</search_query>", "</answer>"])
    response = ai_message.content

    if "<answer>" in response:
        # Hack for fix the answer tag
        prompt = FIX_ANSWER_TAG_INSTRUCTION.format(input=response)
        messages = [HumanMessage(prompt)]
        fixed_msg = LITE_MODEL.invoke(messages)

        # Hack for removing extra xml code block mark
        response = remove_xml_blocks(fixed_msg.content)
        answer = extract_content(response, "answer")
        state["answer"] = answer
        ai_message.content = response
        return Command(
            goto=END,
            update={"messages": [ai_message], "answer": state["answer"]}
        )
    elif "<plan>" in response:
        response += "</plan>"
        ai_message.content = response
        state["plan_goal"] = extract_content(response, "plan")
        return Command(
            goto="plan",
            update={"messages": [ai_message], "plan_goal": state["plan_goal"]}
        )
    elif state["plan_query_index"] != -1:
        if "<search_query>" in response:
            response += "</search_query>"
            query = extract_content(response, "search_query")
        elif "<plan_result>" in response:
            response += "</plan_result>"
            plan_list = state["plan_result"]
            query = plan_list[state["plan_query_index"]]
            ai_message.content = f"{response}\n\n<search_query>{query}</search_query>\n\n"
            state["plan_query_index"] += 1
            if state["plan_query_index"] == len(plan_list):
                state["plan_query_index"] = -1

        state["search_query"] = query
        return Command(
            goto="search",
            update={"messages": [ai_message],
                    "search_query": state["search_query"],
                    "plan_query_index": state["plan_query_index"]}
        )
    elif state["plan_query_index"] == -1 and "<search_query>" in response:
        response += "</search_query>"
        ai_message.content = response
        state["search_query"] = extract_content(response, "search_query")
        return Command(
            goto="search",
            update={"messages": [ai_message],
                    "search_query": state["search_query"]}
        )


def plan(state: AgentState) -> Command[Literal["master"]]:
    plan_goal = state["plan_goal"]

    prompt = PLANNING_INSTRUCTION.format(question=plan_goal)
    message = [HumanMessage(prompt)]
    ai_message = MODEL.invoke(message)

    response = ai_message.content.strip()
    json_str = extract_last_json_block(response)
    plan_list = extract_plan_result(json_str)

    state["plan_result"] = plan_list
    state["plan_query_index"] = 0
    ai_message = AIMessage(
        f"<plan_result>\n{response}\n</plan_result>"
    )
    return Command(
        goto="master",
        update={"messages": [ai_message], "plan_result": state["plan_result"],
                "plan_query_index": state["plan_query_index"]}
    )


async def search(state: AgentState) -> Command[Literal["master"]]:
    query = state["search_query"]
    serp_search_client = create_search_api(
        search_provider="serper",
        serper_api_key=WEB_SEARCH_API_KEY
    )

    sources = serp_search_client.get_sources(query)
    source_processor = SourceProcessor(reranker="jina")

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
    ai_message = MODEL.invoke(summary_messages)
    response = ai_message.content.strip()
    state["search_summary"] = response

    ai_message = AIMessage(
        f"<search_result>{ai_message.content}</search_result>")
    return Command(
        goto="master",
        update={"messages": [ai_message], "search_summary": state["search_summary"],
                "current_iter": state["current_iter"] + 1}
    )


WEB_SEARCH_API_KEY = os.environ["WEB_SEARCH_API_KEY"]
MODEL = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-04-17",
    temperature=0.2
)
LITE_MODEL = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-001",
    temperature=0.2
)

builder = StateGraph(AgentState)
builder.add_node("master", master)
builder.add_node("plan", plan)
builder.add_node("search", search)

builder.add_edge(START, "master")

graph = builder.compile()
