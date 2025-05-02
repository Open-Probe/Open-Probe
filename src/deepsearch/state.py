from typing import Annotated, Sequence, TypedDict
from typing_extensions import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    current_iter: int
    max_iter: int
    search_query: str
    search_summary: str
    answer: str
