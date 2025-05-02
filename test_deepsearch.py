import os
import sys

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src", "deepsearch"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from langchain_core.messages import HumanMessage

from graph import graph
from utils import extract_answer


question = "Which magazine was started first Arthur's Magazine or First for Women?"
res = graph.invoke({
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