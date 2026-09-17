import os
import re
from typing import Annotated, Sequence, TypedDict, List, Literal, Dict, Optional, Any

from langchain_experimental.utilities import PythonREPL
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.types import Command

from .web_search.context_builder import build_context
from .web_search.serp_search import create_search_api
from .web_search.source_processor import SourceProcessor
from .prompt import (
    PLAN_SYSTEM_PROMPT,
    SOLVER_PROMPT,
    SUMMARY_INSTRUCTION,
    QA_PROMPT,
    CODE_SYSTEM_PROMPT,
    CODE_INSTRUCTION,
    REPLAN_INSTRUCTION,
    REFLECTION_INSTRUCTION,
    QUESTION_REWORD_INSTRUCTION,
    COMMONSENSE_INSTRUCTION,
    EXPLANATION_ANSWER
,
)
from .sonic_tls import sonic_http_clients, trust_source
from .utils import extract_content, remove_think_cot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY")
SONIC_JWT = os.getenv("SONIC_JWT")
SONIC_BASE_URL = os.getenv("SONIC_BASE_URL")
SONIC_PLAN_MODEL = os.getenv("SONIC_PLAN_MODEL", "claude-opus-5")
SONIC_COMMON_MODEL = os.getenv("SONIC_COMMON_MODEL", "claude-sonnet-5")
SONIC_CODE_MODEL = os.getenv("SONIC_CODE_MODEL", "claude-sonnet-5")
MAX_SOURCES_PER_SEARCH = int(os.getenv("MAX_SOURCES_PER_SEARCH", "2"))

# Constants
REGEX_PATTERN = r"Plan:\s*(.+)\s*(#E\d+)\s*=\s*(\w+)\s*\[([^\]]+)\]"
EVIDENCE_PATTERN = r"#E\d+"

# Printed by the REPL only if the generated code ran to completion. PythonREPL
# reports failures as an ordinary return value, so this is how we tell a crash
# apart from real output.
REPL_SUCCESS_SENTINEL = "__OPENPROBE_REPL_OK__"


class ReWOOState(TypedDict):
    """State definition for the ReWOO agent workflow."""
    messages: Annotated[Sequence[AnyMessage], add_messages]
    task: str
    plan_string: str
    steps: List
    results: dict
    sources: Optional[List]  # Store processed sources from search
    result: str
    intermediate_result: str
    search_query: str
    needs_replan: bool
    replan_iter: int
    max_replan_iter: int
    reflection: str
    explaination: str


def _sonic_model(model_id: str, temperature: float) -> BaseLanguageModel:
    """
    Build a chat client against Sonic's OpenAI-compatible /chat/completions surface.

    The credential goes only in the OpenAI `api_key` slot, which the SDK sends as
    `Authorization: Bearer`. Sonic picks PAT vs Entra JWT off the *token shape*, not
    the header, so that one slot accepts either. Do not also set an `api-key` header:
    Sonic checks it first and treats it as a PAT-only lookup, so a JWT there 401s
    before `Authorization` is ever read.

    `sonic_http_clients()` supplies the trust anchors. Sonic sits behind a private
    internal CA that certifi does not carry, and httpx defaults to certifi, so
    without it every call fails as `APIConnectionError: Connection error.` with the
    certificate error hidden underneath. See `sonic_tls`.
    """
    return ChatOpenAI(
        model=model_id,
        temperature=temperature,
        api_key=SONIC_JWT,
        base_url=SONIC_BASE_URL,
        **sonic_http_clients(),
    )


def initialize_models() -> Dict[str, BaseLanguageModel]:
    """
    Initialize the language models used by the graph, all served by Sonic.

    Returns:
        Dict containing the models for different functions
    """
    if not SONIC_JWT:
        raise ValueError(
            "SONIC_JWT is not set. For testing, acquire a Personal Access Token "
            "from the Sonic Self-Service Auth Manager at "
            "/authmanager/manage-keys and set it in your environment or .env "
            "file. Production traffic requires an Entra OAuth/JWT token; the "
            "same variable takes either."
        )

    # Name the trust source up front: a TLS failure here surfaces as an opaque
    # `APIConnectionError: Connection error.`, so this line is what tells you
    # whether the certificate chain was ever going to validate.
    print(f"Using Sonic API models (TLS: {trust_source()})\n")

    return {
        "plan": _sonic_model(SONIC_PLAN_MODEL, 0.2),
        "common": _sonic_model(SONIC_COMMON_MODEL, 0.2),
        "code": _sonic_model(SONIC_CODE_MODEL, 0.1),
    }


# Initialize models
MODELS = initialize_models()
PLAN_MODEL = MODELS["plan"]
COMMON_MODEL = MODELS["common"]
CODE_MODEL = MODELS["code"]

# Determine reranker type based on environment
if os.getenv("RERANKER_SERVER_HOST_IP") and os.getenv("RERANKER_SERVER_PORT"):
    RERANKER_TYPE = "local"
else:
    RERANKER_TYPE = "jina"

# Warning: This executes code locally, which can be unsafe when not sandboxed
PY_REPL = PythonREPL()


def extract_last_python_block(input_str: str) -> Optional[str]:
    """
    Extract the last Python code block from a string.
    
    Args:
        input_str: String that may contain Python code blocks
        
    Returns:
        The last Python block found or None if no blocks found
    """
    # Find all code blocks that might contain python
    py_blocks = re.findall(r'```(?:python)?\s*([\s\S]*?)```', input_str)

    if not py_blocks:
        return None
    return py_blocks[-1].strip()


def python_repl_tool(code: Optional[str]) -> Optional[str]:
    """
    Execute Python code in a REPL environment.

    Args:
        code: Python code to execute

    Returns:
        Output of the code execution, or None if execution failed or the code
        produced no output to use as evidence
    """
    if not code or not code.strip():
        print("Failed to execute. Error: no Python code was generated")
        return None

    # PythonREPL returns the traceback as its output instead of raising, and
    # returns "" for code that computes without printing. Both look like
    # success to a bare `is None` check, so append a sentinel print that only
    # runs if the generated code completed.
    instrumented = f"{code}\nprint({REPL_SUCCESS_SENTINEL!r})"
    try:
        output = PY_REPL.run(instrumented)
    except BaseException as e:
        print(f"Failed to execute. Error: {repr(e)}")
        return None

    if output is None or REPL_SUCCESS_SENTINEL not in output:
        print(f"Failed to execute. Error: {output!r}")
        return None

    result = output.replace(REPL_SUCCESS_SENTINEL, "").strip()
    if not result:
        print("Failed to execute. Error: code ran but printed no result")
        return None
    return result


def substitute_evidence(text: str, results: Dict[str, str]) -> str:
    """
    Replace #E variable references in text with their resolved values.

    Substituting each key in turn would let #E1 overwrite the prefix of #E10,
    so references are matched as whole tokens in a single pass. Unresolved
    references are left untouched.

    Args:
        text: Text that may contain #E references
        results: Mapping of step name (e.g. "#E1") to its result

    Returns:
        Text with every known #E reference replaced
    """
    if not text:
        return text

    def _replace(match: re.Match) -> str:
        key = match.group(0)
        value = results.get(key)
        return key if value is None else str(value)

    return re.sub(EVIDENCE_PATTERN, _replace, text)


def reword_tool_input(tool_input: str) -> str:
    """
    Reword a tool input to make it more suitable for search.
    
    Args:
        tool_input: Original tool input text
        
    Returns:
        Reworded search query
    """
    prompt = QUESTION_REWORD_INSTRUCTION.format(tool_input=tool_input)
    response = COMMON_MODEL.invoke(prompt)
    return extract_content(response.content.strip(), "reworded_query")


def master(state: ReWOOState) -> Command[Literal["plan", "search", "code", "solve", "replan", END]]:
    """
    Main decision-making node that determines the next step in the workflow.
    
    Args:
        state: Current agent state
        
    Returns:
        Command directing to the appropriate next node
    """
    # Check if replanning is needed
    if state["needs_replan"] and state["replan_iter"] < state["max_replan_iter"]:
        return Command(
            goto="replan",
        )
    if state["needs_replan"] and state["replan_iter"] >= state["max_replan_iter"]:
        return Command(
            goto="master",
            update={
                "result": "Exhausted all replanning attempts, model failed to solve the task",
                "needs_replan": False
                }
        )
    
    # Check if we have a final result
    if state["result"] is not None:
        return Command(
            goto=END
        )
    
    # Check if we need to create a plan
    if len(state["steps"]) == 0:
        return Command(
            goto="plan"
        )
    
    # Check if all steps are completed
    if len(state["results"]) == len(state["steps"]):
        return Command(
            goto="solve"
        )

    # Process the current step
    current_step = len(state["results"])
    _, step_name, tool, tool_input = state["steps"][current_step]
    result_dict = state["results"]

    print("\n======RESULT DICTIONARY=======\n", result_dict)

    # Resolve any #E references in the current tool_input to their results
    tool_input = substitute_evidence(tool_input, result_dict)

    # Route to appropriate tool
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
        response = PLAN_MODEL.invoke([HumanMessage(prompt)])
        response = response.content.strip()
        result = extract_content(response, "answer")
        print("=========LLM TOOL RESPONSE=========\n", response)
        if "<replan>" in response:
            return Command(
                goto="master",
                update={"needs_replan": True}
            )

        if result is None:
            result = response
        result_dict[step_name] = str(result)

    return Command(
        goto="master",
        update={"results": result_dict}
    )


def replan(state: ReWOOState) -> Command[Literal["plan"]]:
    """
    Generate a reflection on the current plan and prepare for replanning.
    
    This node is called when:
    1. "<replan>" is detected in LLM response
    2. Search results are not satisfactory
    3. Code execution fails
    
    Args:
        state: Current agent state
        
    Returns:
        Command to navigate to the plan node with updated state
    """
    print("=========REPLAN NODE=========")
    
    # Generate reflection if it doesn't exist
    if not state.get("reflection"):
        reflection_prompt = REFLECTION_INSTRUCTION.format(task=state["task"], prev_plan=state["plan_string"])
        reflection_response = PLAN_MODEL.invoke([HumanMessage(reflection_prompt)])
        reflection = reflection_response.content.strip()
        print("=========REFLECTION=========\n", reflection)
    else:
        reflection = state["reflection"]
    
    # Update replan state
    replan_iter = state.get("replan_iter", 0) + 1
    
    return Command(
        goto="plan",
        update={
            "needs_replan": True, 
            "reflection": reflection,
            "replan_iter": replan_iter
        }
    )


def plan(state: ReWOOState) -> Command[Literal["master"]]:
    """
    Generate a plan for solving the task.
    
    Args:
        state: Current agent state
        
    Returns:
        Command to navigate to the master node with the generated plan
    """
    task = state["task"]

    # Choose the appropriate prompt based on whether we're replanning
    if not state["needs_replan"]:
        prompt = QA_PROMPT.format(task=task)
    else:
        prompt = REPLAN_INSTRUCTION.format(
            task=task, prev_plan=state["plan_string"], reflection=state["reflection"])

    # Generate the plan
    result = PLAN_MODEL.invoke(
        [SystemMessage(PLAN_SYSTEM_PROMPT), HumanMessage(prompt)])
    
    result.content = remove_think_cot(result.content)
    print("==========PLAN==========\n", result.content)

    # Parse plan steps
    matches = re.findall(REGEX_PATTERN, result.content)

    # Update state with plan
    update_dict = {"steps": matches, "plan_string": result.content}
    if state["needs_replan"]:
        # Clean old states when replanning
        extra_dict = {
            "needs_replan": False,
            "results": {},
            "sources": None,
            "result": None,
            "intermediate_result": None,
            "search_query": None,
            "reflection": None
        }
        update_dict.update(extra_dict)

    return Command(
        goto="master",
        update=update_dict
    )


async def search(state: ReWOOState) -> Command[Literal["master", "replan"]]:
    """
    Perform web search based on the query and process the results.

    Args:
        state: The current agent state

    Returns:
        Command to navigate back to the master node with search results
        or to the replan node if results are unsatisfactory
    """
    print("\n========= SEARCH NODE =========\n")
    query = state["search_query"]
    print(f"🔍 Searching for: {query}")

    # Initialize search client
    serp_search_client = create_search_api(
        search_provider="serper",
        serper_api_key=WEB_SEARCH_API_KEY
    )

    # Get and process sources
    print("🌐 Getting sources from search API")
    sources_result = serp_search_client.get_sources(query)

    # Validate search result
    if (not sources_result) or getattr(sources_result, "failed", False) or (not getattr(sources_result, "data", None)):
        error_message = getattr(sources_result, "error", "Unknown error from search provider")
        print(f"ERROR: Search API failed or returned no data - {error_message}")
        return Command(
            goto="master",
            update={"needs_replan": True}
        )

    sources_data = sources_result.data

    # Log the sources found
    organic_results = sources_data.get('organic', []) if isinstance(sources_data, dict) else []
    if organic_results:
        print(f"Found {len(organic_results)} organic search results")
    else:
        print("No organic search results found")

    source_processor = SourceProcessor(reranker=RERANKER_TYPE)

    print("Processing sources and building context...")
    max_sources = MAX_SOURCES_PER_SEARCH
    processed_sources = await source_processor.process_sources(
        sources_result,
        max_sources,
        query,
        pro_mode=True
    )

    # Build context from processed sources
    print("🏗️  Building context from processed sources")
    context = build_context(processed_sources)
    print(f"📝 Context built with {len(context)} characters")

    # Generate summary of search results
    prompt = SUMMARY_INSTRUCTION.format(
        task=query, context=context
    )
    summary_messages = [
        HumanMessage(prompt)
    ]

    print("🤖 Generating search summary...")
    ai_message = COMMON_MODEL.invoke(summary_messages)
    response = ai_message.content.strip()
    result = extract_content(response, "answer")

    # Check if results are satisfactory
    if result is None:
        result = response
        print("⚠️  Search results were not satisfactory, triggering replan")
        print("\n======NOT SATISFACTORY RESULT=======\n", result)
        return Command(
            goto="master",
            update={"needs_replan": True}
        )

    print("✅ Search completed successfully")
    print("Search completed, returning to master")

    # Update results with search output
    current_step = len(state["results"])
    _, step_name, _, _ = state["steps"][current_step]
    result_dict = state["results"]
    result_dict[step_name] = result

    return Command(
        goto="master",
        update={
            "results": result_dict,
            "sources": processed_sources.get('organic', [])
        }
    )


def code(state: ReWOOState) -> Command[Literal["master", "replan"]]:
    """
    Generate and execute code based on the task.
    
    Args:
        state: The current agent state
        
    Returns:
        Command to navigate to the master node with code results
        or to the replan node if code execution failed
    """
    query = state["search_query"]
    ai_message = CODE_MODEL.invoke([
        SystemMessage(CODE_SYSTEM_PROMPT),
        HumanMessage(CODE_INSTRUCTION.format(task=query))
    ])

    code_solution = extract_last_python_block(ai_message.content)
    print(f"Code solution:\n{code_solution}")
    result = python_repl_tool(code_solution)

    # Time to replan if code execution failed
    if result is None:
        print("Code execution failed, replanning...")
        return Command(
            goto="master",
            update={"needs_replan": True}
        )

    # Update results with code output
    current_step = len(state["results"])
    _, step_name, _, _ = state["steps"][current_step]
    result_dict = state["results"]
    result_dict[step_name] = result

    return Command(
        goto="master",
        update={"results": result_dict}
    )


def solve(state: ReWOOState) -> Command[Literal["master"]]:
    """
    Generate the final solution based on all collected results.
    
    Args:
        state: The current agent state
        
    Returns:
        Command to navigate to the master node with the final result
    """
    # Construct plan with results
    plan = ""
    for step_plan, step_name, tool, tool_input in state["steps"]:
        result_dict = state["results"]
        tool_input = substitute_evidence(tool_input, result_dict)
        step_name = substitute_evidence(step_name, result_dict)
        plan += f"Plan: {step_plan}\n{step_name} = {tool}[{tool_input}]"
    
    # Generate final solution
    prompt = SOLVER_PROMPT.format(plan=plan, task=state["task"])
    result = PLAN_MODEL.invoke(prompt)
    explaination = COMMON_MODEL.invoke(EXPLANATION_ANSWER.format(plan=plan, result=result.content, task=state["task"]))


    return Command(
        goto="master",
        update={
            "result": result.content,
            "explaination": explaination.content
        }
    )


def create_graph() -> StateGraph:
    """
    Create and return the workflow graph for the ReWOO agent.
    
    Returns:
        Compiled StateGraph instance
    """
    builder = StateGraph(ReWOOState)
    builder.add_node("master", master)
    builder.add_node("plan", plan)
    builder.add_node("search", search)
    builder.add_node("code", code)
    builder.add_node("solve", solve)
    builder.add_node("replan", replan)
    builder.add_edge(START, "master")
    
    return builder.compile()


# Create the compiled graph
graph = create_graph()
