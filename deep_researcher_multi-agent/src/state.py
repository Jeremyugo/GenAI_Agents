from typing import Annotated
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    user_request: Annotated[list, "The user's research request"]
    todos: Annotated[list[str], "List of research tasks"]
    search_queries: Annotated[list[str], "List of web search queries"]
    search_results: Annotated[list[list[str]], "The web search results"]
    writing_plan: Annotated[list, "List of report sections"]
    next: Annotated[str, "The next agent to call"]