import asyncio

from deepsearch.graph import graph
from deepsearch.utils import extract_answer
from langchain_core.messages import HumanMessage


async def solve(question):
    res = await graph.ainvoke({
        "messages": [HumanMessage(f"<question>{question}</question>")],
        "current_iter": 0,
        "max_iter": 5,
        "search_query": None,
        "search_summary": None,
        "answer": None
    })

    for m in res["messages"]:
        m.pretty_print()
    last_msg_line = res["messages"][-1].content.split("\n")[-1]
    answer = extract_answer(last_msg_line)
    if answer is None:
        print("Failed without an answer!")
    print(f"The answer is: {answer}")


query = "Which magazine was started first Arthur's Magazine or First for Women?"
asyncio.run(solve(query))
