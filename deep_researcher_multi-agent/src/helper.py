from langchain_core.language_models.chat_models import BaseChatModel
from typing import Annotated, TypedDict, Literal
from langgraph.types import Command
from src.state import AgentState
from langgraph.graph import END


def make_supervisor_node(llm: BaseChatModel, members: list[str]) -> str:
    options = ["FINISH"] + members
    system_prompt = (
        "You are a research supervisor tasked with routing tasks between the"
        f" following workers: {members}. Given the following research topic,"
        " respond with the worker to act next. Each worker will perform a"
        " task and respond with the results and current_status. When finished,"
        " respond with FINISH."
    )

    class Router(TypedDict):
        """Worker to route to next. If no workers needed, route to FINISH."""

        next: Literal[*options]

    def supervisor_node(state: AgentState) -> Command[Literal[*members, "__end__"]]:
        """An LLM-based router."""
        messages = [
            {"role": "system", "content": system_prompt},
        ] + state["messages"]
        
        response = llm.with_structured_output(Router).invoke(messages)
        goto = response["next"]
        if goto == "FINISH":
            goto = END

        return Command(goto=goto, update={"next": goto})

    return supervisor_node

