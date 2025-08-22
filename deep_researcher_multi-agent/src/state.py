from typing import Annotated
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    topic: Annotated[list, "The user's research request"]
    research_plan: Annotated[str, "The plan to write the research report"]
    search_queries: Annotated[list[str], "List of web search queries"]
    search_results: Annotated[list[list[str]], "The web search results"]
    writing_plan: Annotated[str, "List of report sections"]
    writing_plan_feedback: Annotated[str, "Feedback on the outline structure"]
    writing_plan_and_sources: Annotated[list[str], "Section writing plan and resources"]
    full_report_draft: Annotated[str, "First report draft"]
    current_stage: Annotated[str, "Recently completed stage"]
    next: Annotated[str, "The next agent to call"]