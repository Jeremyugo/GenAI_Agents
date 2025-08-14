import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.state import AgentState
from src.agents.planner import PlanningAgent
from src.helper import make_supervisor_node

from typing import Literal

from langgraph.types import Command
from langgraph.graph import END, StateGraph
from langchain_openai import ChatOpenAI


def planning_node(state: AgentState) -> Command[Literal['supervisor']]:
    planning_agent = PlanningAgent.create_planning_agent()
    result = planning_agent.invoke(state)

    todo_strings = [todo.todo for todo in result['todos']]

    return Command(
        update={'todos': todo_strings},
        goto=END # currently only sub-agent in this team, so we route to END
    )
    
def build_planning_team():    
    planner_supervisor_node = make_supervisor_node(
        llm=ChatOpenAI(model="gpt-4o"), 
        members=['planner',]
    )

    planner_builder = StateGraph(AgentState)
    planner_builder.add_node('supervisor', planner_supervisor_node)
    planner_builder.add_node('planner', planning_node)

    planner_builder.set_entry_point('supervisor')
    planner_supervisor = planner_builder.compile()
    
    return planner_supervisor