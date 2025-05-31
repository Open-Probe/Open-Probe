import os
import re
from typing import Annotated, Sequence, TypedDict, List, Literal

from langchain_experimental.utilities import PythonREPL
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.types import Command

from .web_search.context_builder import build_context
from .web_search.serp_search import create_search_api
from .web_search.source_processor import SourceProcessor
from .rewoo_prompt import (
    PLAN_SYSTEM_PROMPT,
    SOLVER_PROMPT,
    SUMMARY_INSTRUCTION,
    QA_PROMPT,
    CODE_SYSTEM_PROMPT,
    CODE_INSTRUCTION,
    REPLAN_INSTRUCTION,
    QUESTION_REWORD_INSTRUCTION,
    COMMONSENSE_INSTRUCTION
)
from .utils import extract_content
from dotenv import load_dotenv

load_dotenv()

WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("LAMBDA_API_KEY")
OPENAI_API_BASE_URL = "https://api.lambda.ai/v1"

if OPENAI_API_KEY:
    from langchain_openai import ChatOpenAI
    model_id = "deepseek-r1-671b"
    lite_model_id = "llama3.3-70b-instruct-fp8"
    MODEL = ChatOpenAI(
        model=model_id,
        temperature=0.2,
        openai_api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE_URL,
    )
    LITE_MODEL = ChatOpenAI(
        model=lite_model_id,
        temperature=0.2,
        openai_api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE_URL,
    )
else:
    from langchain_google_genai import ChatGoogleGenerativeAI
    model_id = "gemini-2.5-flash-preview-04-17"
    lite_model_id = "gemini-2.0-flash-001"
    MODEL = ChatGoogleGenerativeAI(
        model=model_id,
        temperature=0.2,
        google_api_key=GOOGLE_API_KEY
    )
    LITE_MODEL = ChatGoogleGenerativeAI(
        model=lite_model_id,
        temperature=0.2,
        google_api_key=GOOGLE_API_KEY
    )

if os.getenv("RERANKER_SERVER_HOST_IP") and os.getenv("RERANKER_SERVER_PORT"):
    RERANKER_TYPE = "local"
else:
    RERANKER_TYPE = "jina"

# Regex to match expressions of the form E#... = ...[...]
REGEX_PATTERN = r"Plan:\s*(.+)\s*(#E\d+)\s*=\s*(\w+)\s*\[([^\]]+)\]"

# Warning: This executes code locally, which can be unsafe when not sandboxed
PY_REPL = PythonREPL()


def extract_last_python_block(input_str):
    # Find all code blocks that might contain python
    py_blocks = re.findall(r'```(?:python)?\s*([\s\S]*?)```', input_str)

    if not py_blocks:
        return None
    return py_blocks[-1].strip()


def python_repl_tool(code):
    """Use this to execute python code. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user."""
    try:
        result = PY_REPL.run(code)
        return result
    except BaseException as e:
        print(f"Failed to execute. Error: {repr(e)}")
        return None


class ReWOOState(TypedDict):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    task: str
    plan_string: str
    steps: List
    results: dict
    result: str
    intermediate_result: str
    search_query: str
    needs_replan: bool
    replan_iter: int
    max_replan_iter: int


def master(state: ReWOOState) -> Command[Literal["plan", "search", "code", "solve", END]]:
    if state["needs_replan"] and state["replan_iter"] < state["max_replan_iter"]:
        return Command(
            goto="plan"
        )
    if state["result"] is not None:
        return Command(
            goto=END
        )
    if len(state["steps"]) == 0:
        return Command(
            goto="plan"
        )
    if len(state["results"]) == len(state["steps"]):
        return Command(
            goto="solve"
        )

    current_step = len(state["results"])
    _, step_name, tool, tool_input = state["steps"][current_step]
    result_dict = state["results"]

    print("\n======result_dict=======\n", result_dict)

    # Replace all occurrences of that k in the current tool_input string with v
    for k, v in result_dict.items():
        tool_input = tool_input.replace(k, v)

    print("\n======tool_input=======\n", tool_input)
    if tool == "Search":
        searchable_query = reword_tool_input(tool_input)
        return Command(
            goto="search",
            update={"search_query": searchable_query}
        )
    if tool == "Code":
        return Command(
            goto="code",
            update={"search_query": tool_input}
        )
    if tool == "LLM":
        prompt = COMMONSENSE_INSTRUCTION.format(question=tool_input)
        response = MODEL.invoke([HumanMessage(prompt)])
        response = response.content.strip()
        result = extract_content(response, "answer")
        # Time to replan/reflection/re-search
        if result is None:
            result = response
        result_dict[step_name] = str(result)

    return Command(
        goto="master",
        update={"results": result_dict}
    )


def plan(state: ReWOOState) -> Command[Literal["master"]]:
    task = state["task"]

    if not state["needs_replan"]:
        prompt = QA_PROMPT.format(task=task)
    else:
        prompt = REPLAN_INSTRUCTION.format(
            task=task, prev_plan=state["plan_string"])

    result = MODEL.invoke(
        [SystemMessage(PLAN_SYSTEM_PROMPT), HumanMessage(prompt)])

    print("plan", result.content)

    # Find all matches in the sample text
    matches = re.findall(REGEX_PATTERN, result.content)

    update_dict = {"steps": matches, "plan_string": result.content}
    if state["needs_replan"]:
        # Clean old states
        extra_dict = {
            "needs_replan": False,
            "results": {},
            "result": None,
            "intermediate_result": None,
            "search_query": None,
            "replan_iter": state["replan_iter"] + 1
        }
        update_dict.update(extra_dict)

    return Command(
        goto="master",
        update=update_dict
    )


async def search(state: ReWOOState) -> Command[Literal["master"]]:
    """
    Perform web search based on the query and process the results.

    Args:
        state: The current agent state

    Returns:
        Command to navigate back to the master node with search results
    """
    print("\n==== SEARCH NODE ====")
    query = state["search_query"]
    print(f"Searching for: {query}")

    # Initialize search client
    serp_search_client = create_search_api(
        search_provider="serper",
        serper_api_key=WEB_SEARCH_API_KEY
    )

    # Get and process sources
    print("Getting sources from search API")
    sources = serp_search_client.get_sources(query)

    source_processor = SourceProcessor(reranker=RERANKER_TYPE)

    print("Processing sources and building context...")
    max_sources = 2
    processed_sources = await source_processor.process_sources(
        sources,
        max_sources,
        query,
        pro_mode=True
    )

    # Build context from processed sources
    context = build_context(processed_sources)

    # Generate summary of search results
    prompt = SUMMARY_INSTRUCTION.format(
        task=query, context=context
    )
    summary_messages = [
        HumanMessage(prompt)
    ]

    print("Generating search summary...")
    ai_message = MODEL.invoke(summary_messages)
    response = ai_message.content.strip()
    result = extract_content(response, "answer")

    # Time to replan/reflection/re-search
    if result is None:
        result = response
        print("\n======Not satisfactory result=======\n", result)
        state["needs_replan"] = True

    print("Search completed, returning to master")

    current_step = len(state["results"])
    _, step_name, _, _ = state["steps"][current_step]
    result_dict = state["results"]
    result_dict[step_name] = result

    return Command(
        goto="master",
        update={"results": result_dict, "needs_replan": state["needs_replan"]}
    )


def code(state: ReWOOState) -> Command[Literal["master"]]:
    query = state["search_query"]
    ai_message = MODEL.invoke([
        SystemMessage(CODE_SYSTEM_PROMPT),
        HumanMessage(CODE_INSTRUCTION.format(task=query))
    ])

    code_solution = extract_last_python_block(ai_message.content)
    print(f"Code solution:\n{code_solution}")
    result = python_repl_tool(code_solution)

    # Time to replan/reflection/re-code
    if result is None:
        result = "I don't know."
        state["needs_replan"] = True

    current_step = len(state["results"])
    _, step_name, _, _ = state["steps"][current_step]
    result_dict = state["results"]
    result_dict[step_name] = result

    return Command(
        goto="master",
        update={"results": result_dict, "needs_replan": state["needs_replan"]}
    )


def solve(state: ReWOOState) -> Command[Literal["master"]]:
    plan = ""
    for step_plan, step_name, tool, tool_input in state["steps"]:
        result_dict = state["results"]
        for k, v in result_dict.items():
            tool_input = tool_input.replace(k, v)
            step_name = step_name.replace(k, v)
        plan += f"Plan: {step_plan}\n{step_name} = {tool}[{tool_input}]"
    prompt = SOLVER_PROMPT.format(plan=plan, task=state["task"])
    result = MODEL.invoke(prompt)

    return Command(
        goto="master",
        update={"result": result.content}
    )


def reword_tool_input(tool_input):
    prompt = QUESTION_REWORD_INSTRUCTION.format(tool_input=tool_input)
    response = LITE_MODEL.invoke(prompt)
    return extract_content(response.content.strip(), "reworded_query")


builder = StateGraph(ReWOOState)
builder.add_node("master", master)
builder.add_node("plan", plan)
builder.add_node("search", search)
builder.add_node("code", code)
builder.add_node("solve", solve)
builder.add_edge(START, "master")

graph = builder.compile()
