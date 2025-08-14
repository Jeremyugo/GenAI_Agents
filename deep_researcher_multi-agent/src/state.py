from typing import Annotated
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    user_request: Annotated[list, "The user's research request"]
    todos: Annotated[list[str], "List of research tasks"]
    next: Annotated[str, "The next agent to call"]