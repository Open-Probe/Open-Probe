import os
from typing import Literal

"""
DeepSearch Graph Implementation

This module defines the LangGraph workflow for DeepSearch, with capabilities for:
- Multi-step planning for complex queries
- Web search based on generated plans
- Adaptive replanning when initial searches are insufficient
- Reflection on previous plans to improve search strategy

The graph workflow includes these main nodes:
- master: Central decision-making node for routing
- plan: Generates search plans from queries
- search: Executes web searches and processes results

The replanning feature allows the model to:
1. Analyze why previous searches were insufficient
2. Reflect on what information is missing
3. Generate improved search queries
4. Continue the search process with better strategy
"""

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from .prompt import (
    MASTER_SYSTEM_PROMPT,
    PLANNING_INSTRUCTION,
    REPLAN_INSTRUCTION,
    SUMMARY_SYSTEM_PROMPT,
    ANSWER_OR_REPLAN_PROMPT
)
from .state import AgentState
from .utils import (
    extract_content,
    extract_last_json_block,
    extract_plan_result,
)
from .web_search.context_builder import build_context
from .web_search.serp_search import create_search_api
from .web_search.source_processor import SourceProcessor

# Load environment variables
load_dotenv()
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
openai_api_key = os.getenv("LAMBDA_API_KEY")
openai_api_base = "https://api.lambda.ai/v1"
openai_model = "deepseek-r1-671b"
# Initialize models
if openai_api_key:
    from langchain_openai import ChatOpenAI
    print("Using LAMBDA_API")
    MODEL = ChatOpenAI(
        model=openai_model,
        temperature=0.2,
        openai_api_key=openai_api_key,
        base_url=openai_api_base,
    )
else:
    MODEL = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-preview-04-17",
        temperature=0.2,
        google_api_key=GOOGLE_API_KEY
    )

def extract_reflection(text: str) -> str:
    """Extract reflection content from text."""
    return extract_content(text, "reflection")

def decide_action(state: AgentState) -> Command[Literal["search", "master"]]:
    """
    Determine the next action based on the current state.
    
    Args:
        state: The current agent state
        
    Returns:
        Command to navigate to the next node in the graph
    """
    print("\n==== DECIDE_ACTION ====")
    response = state["messages"][-1].content
    ai_message = state["messages"][-1]
    print(f"Current response: {response}")
    print(f"Plan query index: {state['plan_query_index']}")
    
    # Handle plan-based search queries
    if state["plan_query_index"] != -1:
        plan_list = state["plan_result"]
        
        if "<plan_result>" in response or "<search_result>" in response or "<reflection>" in response:
            query = plan_list[state["plan_query_index"]]
            print(f"Selected query from plan: {query}")
            ai_message = AIMessage(f"<search_query>{query}</search_query>")
            
            # Update plan query index
            state["plan_query_index"] += 1
            if state["plan_query_index"] == len(plan_list):
                state["plan_query_index"] = -1
                print("Reached end of plan queries")
                
            state["search_query"] = query
            return Command(
                goto="search",
                update={
                    "messages": [ai_message],
                    "search_query": state["search_query"],
                    "plan_query_index": state["plan_query_index"]
                }
            )
    
    # Handle completed search with results
    elif state["plan_query_index"] == -1 and "<search_result>" in response:
        print("Search completed, moving to master")
        state["search_summary"] = response
        ai_message = AIMessage(ANSWER_OR_REPLAN_PROMPT)

        return Command(
            goto="master",
            update={
                "messages": [ai_message], 
                "search_summary": state["search_summary"]
            }
        )
  

def master(state: AgentState) -> Command[Literal["plan", "search", END]]:
    """
    Main decision-making node that processes messages and decides next steps.
    
    Args:
        state: The current agent state
        
    Returns:
        Command to navigate to the appropriate node
    """
    print("\n==== MASTER NODE ====")
    messages = [SystemMessage(MASTER_SYSTEM_PROMPT)] + state["messages"]
    print(f"Last message: {state['messages'][-1].content}")
    
    # Check if we need to decide an action based on previous response
    if "<plan_result>" in messages[-1].content or "<search_result>" in messages[-1].content:
        print("Inside Decide Action")
        return decide_action(state)
    
    # Generate a new response
    ai_message = MODEL.invoke(
        messages, stop=["</plan>", "</plan_result>", "</search_query>", "</answer>", "</replan>"])
    response = ai_message.content
    
    # Handle case where content is a list of candidates
    if isinstance(response, list):
        print(f"Response is a list: {response}")
        response = response[-1]
        ai_message.content = response

    print(f"Generated response: {response}...")

    # Process the response based on tags
    if "<answer>" in response:
        print("Found answer tag")
        response += "</answer>"
        answer = extract_content(response, "answer")
        print(f"Extracted answer: {answer}...")
        state["answer"] = answer
        ai_message.content = response
        return Command(
            goto=END,
            update={"messages": [ai_message], "answer": state["answer"]}
        )
    elif "<plan>" in response:
        print("Found plan tag")
        response += "</plan>"
        ai_message.content = response
        state["plan_goal"] = extract_content(response, "plan")
        # Initialize replan values to defaults
        state["needs_replan"] = False
        state["previous_plan"] = []
        state["reflection"] = ""
        state["replan_count"] = 0
        return Command(
            goto="plan",
            update={
                "messages": [ai_message], 
                "plan_goal": state["plan_goal"],
                "needs_replan": False,
                "previous_plan": [],
                "reflection": "",
                "replan_count": 0
            }
        )
    elif "<replan>" in response:
        print("Found replan tag")
        
        # Check if we've reached the replan limit
        if (openai_api_key and openai_model == "deepseek-r1-671b") or state.get("replan_count", 0) >= 2:
            print("Replan limit reached (2), forcing answer")
            # Force the model to answer with what it has
            ai_message = AIMessage(
                " ".join([
                    "You've already replanned twice, which is the maximum allowed.",
                    "Please provide your best answer with the information you have gathered so far."
                ])
            )
            return Command(
                goto="master",
                update={"messages": [ai_message]}
            )
        
        response += "</replan>"
        ai_message.content = response
        # Store the current plan as previous plan
        state["previous_plan"] = state["plan_result"]
        state["needs_replan"] = True
        # Keep the same plan goal but increment replan count
        replan_count = state.get("replan_count", 0) + 1
        print(f"Replanning attempt {replan_count}/2")
        
        return Command(
            goto="plan",
            update={
                "messages": [ai_message],
                "previous_plan": state["plan_result"],
                "needs_replan": True,
                "replan_count": replan_count
            }
        )
    else:
        print("No specific tags found, deciding action")
        return decide_action(state)


def plan(state: AgentState) -> Command[Literal["master"]]:
    """
    Generate a plan for answering the query.
    
    Args:
        state: The current agent state
        
    Returns:
        Command to navigate back to the master node with the plan
    """
    print("\n==== PLAN NODE ====")
    
    # Check if we're replanning or doing initial planning
    if state["needs_replan"]:
        replan_count = state.get("replan_count", 1)
        print(f"Replanning attempt {replan_count}/2")
        
        # Format previous plan for the prompt
        previous_plan_str = "\n".join([f"{i+1}. {query}" for i, query in enumerate(state["previous_plan"])])
        
        # Use the replan instruction
        prompt = REPLAN_INSTRUCTION.format(
            question=state["plan_goal"],
            previous_plan=previous_plan_str,
            search_summary=state["search_summary"]
        )
        
        message = [HumanMessage(prompt)]
        ai_message = MODEL.invoke(message)
        response = ai_message.content.strip()
        
        # Extract reflection if present
        if "<reflection>" in response:
            reflection = extract_reflection(response)
            state["reflection"] = reflection
            print(f"Reflection: {reflection}")
        
        # Extract the new plan
        json_str = extract_last_json_block(response)
        plan_list = extract_plan_result(json_str)
        print(f"New plan created: {plan_list}")
        
        # Update state with the new plan
        state["plan_result"] = plan_list
        state["plan_query_index"] = 0
        state["needs_replan"] = False
        
        # Create response message with reflection and replan count
        ai_message = AIMessage(
            f"<reflection>\nReplan attempt {replan_count}/2: {state['reflection']}\n</reflection>\n\n<plan_result>\n{response}\n</plan_result>"
        )
    else:
        print("Creating initial plan")
        plan_goal = state["plan_goal"]
        print(f"Planning for goal: {plan_goal}")
        
        prompt = PLANNING_INSTRUCTION.format(question=plan_goal)
        message = [HumanMessage(prompt)]
        
        ai_message = MODEL.invoke(message)
        response = ai_message.content.strip()
        
        json_str = extract_last_json_block(response)
        plan_list = extract_plan_result(json_str)
        print(f"Plan created: {plan_list}")

        state["plan_result"] = plan_list
        state["plan_query_index"] = 0
        state["replan_count"] = 0
        
        ai_message = AIMessage(f"<plan_result>\n{response}\n</plan_result>")
    
    return Command(
        goto="master",
        update={
            "messages": [ai_message], 
            "plan_result": state["plan_result"],
            "plan_query_index": state["plan_query_index"],
            "needs_replan": state["needs_replan"],
            "reflection": state.get("reflection", ""),
            "replan_count": state.get("replan_count", 0)
        }
    )


async def search(state: AgentState) -> Command[Literal["master"]]:
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

    
    reranker_ip = os.getenv("RERANKER_SERVER_HOST_IP")
    reranker_port = os.getenv("RERANKER_SERVER_PORT")
    if reranker_ip and reranker_port:
        source_processor = SourceProcessor(reranker="local")
    else:
        source_processor = SourceProcessor(reranker="jina")
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
    summary_messages = [
        SystemMessage(SUMMARY_SYSTEM_PROMPT),
        HumanMessage(context)
    ]
    
    print("Generating search summary...")
    ai_message = MODEL.invoke(summary_messages)
    response = ai_message.content.strip()
    state["search_summary"] = response

    ai_message = AIMessage(f"<search_result>{response}</search_result>")
    print("Search completed, returning to master")
    
    return Command(
        goto="master",
        update={
            "messages": [ai_message], 
            "search_summary": state["search_summary"],
            "current_iter": state["current_iter"] + 1
        }
    )


# Build the agent graph
builder = StateGraph(AgentState)
builder.add_node("master", master)
builder.add_node("plan", plan)
builder.add_node("search", search)
builder.add_edge(START, "master")

# Compile the graph
graph = builder.compile()
