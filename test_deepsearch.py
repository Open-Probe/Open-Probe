import asyncio
from deepsearch.utils import extract_content
from deepsearch.graph import graph


async def solve(question):
    
    res = await graph.ainvoke({
        "task": question,       
        "plan_string": None,
        "steps": [],
        "results": {},
        "result": None,
        "intermediate_result": None,
        "search_query": None,
        "needs_replan": False,
        "reflection": None,
        "sources": None,
        "explaination": None,
        "replan_iter": 0,
        "max_replan_iter": 1
    }, {"recursion_limit": 30})

    print(res)
    # print(res["plan_string"])
    # print(res["results"])

    response = res["result"]
    explaination = res["explaination"]
    print(f"The explaination is: {explaination}")
    answer = extract_content(response, "answer")
    if answer is None:
        print("Failed without an answer!")  
    print(f"The answer is: {answer}")

#Sample query to test the code
# query = "If my future wife has the same first name as the 15th first lady of the United States' mother and her surname is the same as the second assassinated president's mother's maiden name, what is my future wife's name? "
query = """In feet, subtract the diameter of the pitching plate ("rubber") in softball, from the distance between the "points" of the bases in baseball, and multiply that figure by the year that Joe DiMaggio married Marilyn Monroe. """
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(solve(query))
    finally:
        # Cancel all pending tasks and close loop properly
        pending = asyncio.all_tasks(loop=loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

