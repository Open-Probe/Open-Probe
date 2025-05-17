from typing import Annotated, Sequence, TypedDict, List
from typing_extensions import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    current_iter: int
    max_iter: int
    plan_goal: str
    plan_result: List[str]
    plan_query_index: int
    search_query: str
    search_summary: str
    answer: str
    needs_replan: bool
    previous_plan: List[str]
    reflection: str
    replan_count: int
