import asyncio

from langchain_core.messages import HumanMessage
from deepsearch.prompt import MULTIHOP_QA_INSTRUCTION
from deepsearch.utils import extract_content
from deepsearch.graph import graph


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
        "reflection": ""
    })

    for m in res["messages"]:
        m.pretty_print()

    response = res["messages"][-1].content
    answer = extract_content(response, "answer")
    if answer is None:
        print("Failed without an answer!")  
    print(f"The answer is: {answer}")


# query = "Which magazine was started first Arthur's Magazine or First for Women?"
# query = "who was the one to invent rubik's cube"
query = "How much tin (kg) with 100 kg copper can lower the mixture’s melting point to 800 celcius?"
# query = "How many meters taller is the Burj Khalifa compared to taj mahal and what would be the square root of that number times the sum of both the structures"
asyncio.run(solve(query))
