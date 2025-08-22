import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.state import AgentState
from src.agents.planner import PlanningAgent
from src.agents.researcher import ResearchAgent
from src.agents.writer import WritingAgent
from src.helper import make_supervisor_node
from langchain_core.messages import HumanMessage

from typing import Literal

from langgraph.types import Command
from langgraph.graph import END, StateGraph
from langchain_openai import ChatOpenAI


def plan_node(state: AgentState) -> Command[Literal['supervisor']]:   
    message = HumanMessage(
            content="The plan to work on the research topic is complete. We can now move on to the research phase.",
            name="plan"
        )
    
    plan_agent = PlanningAgent.create_agent()
    result = plan_agent.invoke(state)
    
    research_plan = result.get('research_plan', '')
    writing_plan = result.get('writing_plan', '')
    
    return Command(
        update={
            'research_plan': research_plan,
            'writing_plan': writing_plan,
            'current_stage': 'planning_complete',
            'messages': [message]
        },
        goto='supervisor'
    )
    
    
async def research_node(state: AgentState) -> Command[Literal['supervisor']]:
    message = HumanMessage(
            content="The research phase is now complete. We can now move on to the write phase",
            name="research"
        )
    
    research_agent = ResearchAgent.create_agent()
    result = await research_agent.ainvoke(state)
    
    writing_plan_and_sources = result.get('writing_plan_and_sources', '')
    
    return Command(
        update={
            'writing_plan_and_sources': writing_plan_and_sources,
            'current_stage': 'research_completed',
             'messages': [message]
        },
        goto='supervisor'
    )
    
    
async def write_node(state: AgentState) -> Command[Literal['supervisor']]:
    message = HumanMessage(
            content="The research report has been drafted. We can now end the run by calling 'FINISH'",
            name='write'
        )
        
    write_agent = WritingAgent.create_agent()
    result = await write_agent.ainvoke(state)
    
    full_report_draft = result.get('full_report_draft', '')
    
    return Command(
        update={
            'full_report_draft': full_report_draft,
            'current_stage': 'writing_completed',
             'messages': [message]
        },
        goto='supervisor'
    )
    
     
def build_research_team():
    research_supervisor_node = make_supervisor_node(
        llm=ChatOpenAI(model="gpt-4o"),
        members=['plan', 'research', 'write']
    )
    
    graph = (
        StateGraph(AgentState)
        .add_node('supervisor', research_supervisor_node)
        .add_node('plan', plan_node)
        .add_node('research', research_node)
        .add_node('write', write_node)
        .set_entry_point('supervisor')
    ).compile()
    
    return graph