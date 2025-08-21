from typing import Annotated
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    user_request: Annotated[list, "The user's research request"]
    research_plan: Annotated[str, "The plan to write the research report"]
    search_queries: Annotated[list[str], "List of web search queries"]
    search_results: Annotated[list[list[str]], "The web search results"]
    writing_plan: Annotated[list, "List of report sections"]
    full_report_draft: Annotated[str, "First report draft"]
    next: Annotated[str, "The next agent to call"]