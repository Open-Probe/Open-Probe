import asyncio

from langchain_core.messages import HumanMessage
from deepsearch.prompt import MULTIHOP_QA_INSTRUCTION
from deepsearch.utils import extract_content
from deepsearch.graph_copy_1 import graph


async def solve(question):
    prompt = MULTIHOP_QA_INSTRUCTION.format(
        question=question)
    res = await graph.ainvoke({
        "messages": [HumanMessage(prompt)],
        "current_iter": 0,
        "max_iter": 5,
        "search_query": "",
        "search_summary": "",
        "answer": "",
        "plan_goal": "",
        "plan_result": [],
        "plan_query_index": -1,
        "needs_replan": False,
        "previous_plan": [],
        "reflection": "",
        "replan_count": 0,
        "task": "",
        "generation": "",
        "error": "",
        "error_iterations": 0
    },
    {"recursion_limit": 40}
    )

    for m in res["messages"]:
        m.pretty_print()

    response = res["messages"][-1].content
    answer = extract_content(response, "answer")
    if answer is None:
        print("Failed without an answer!")  
    print(f"The answer is: {answer}")


# query = "Which magazine was started first Arthur's Magazine or First for Women?"
query = "who was the one to invent rubik's cube"
# query = "How much tin (kg) with 100 kg copper can lower the mixture’s melting point to 800 celcius?"
# query = "How many meters taller is the Burj Khalifa compared to taj mahal and what would be the square root of that number times the sum of both the structures"
# query = "How many 300 passenger planes are needed to carry 1% of New York’s population?"
# query = "According to the latest Smithsonian Global Volcanism Program data, how many erupting volcanoes are currently above 3 000 m, and what fraction of all active volcanoes worldwide does that represent?"
# query = "When is the next transit of Mercury visible from Tokyo (local time), and how many days and hours from now (May 16, 2025, JST) is that event?"
# query = "How many years earlier would Punxsutawney Phil have to be canonically alive to have made a Groundhog Day prediction in the same state as the US capitol"
asyncio.run(solve(query))
