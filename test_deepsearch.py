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
        "plan_goal": None,
        "plan_result": None,
        "plan_query_index": -1,
        "search_query": None,
        "search_summary": None,
        "answer": None
    })

    for m in res["messages"]:
        m.pretty_print()

    response = res["messages"][-1].content
    answer = extract_content(response, "answer")
    if answer is None:
        print("Failed without an answer!")
    print(f"The answer is: {answer}")


query = "Which magazine was started first Arthur's Magazine or First for Women?"
asyncio.run(solve(query))
