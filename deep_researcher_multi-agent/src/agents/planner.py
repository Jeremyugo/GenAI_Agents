import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.state import AgentState
from src.prompts import research_planner_system_prompt

from typing import Annotated
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI

from pydantic import BaseModel, Field


class Todo(BaseModel):
    todo: Annotated[str, "The research plan"]

class TodoList(BaseModel):
    todos: list[Todo] = Field(
        description="A list of all Todos"
    )



class PlanningAgent:
    def __init__(self, model_name: str = "gpt-4o"):
        self.model = ChatOpenAI(model=model_name)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", research_planner_system_prompt),
                ('human', "Here is the research topic: \n\n{topic}. Generate a research plan to explore the topic"),
            ]
        )
        
        self.chain = self.prompt | self.model.with_structured_output(TodoList)
          
    
    def _planning_agent(self, state: AgentState):
        todos = self.chain.invoke(
            {
                'topic': state['messages']
            }
        )
        
        return {
            'todos': todos.todos
        }
        
    
    def build_planning_agent(self,):
        graph_builder = StateGraph(AgentState)

        graph_builder.add_node('planning_agent', self._planning_agent)
        graph_builder.set_entry_point('planning_agent')
        graph_builder.set_finish_point('planning_agent')

        planner_agent = graph_builder.compile()
        
        return planner_agent
    
        
    @classmethod
    def create_planning_agent(cls, model_name: str = "gpt-4o"):
        agent = cls(model_name=model_name)
        return agent.build_planning_agent()
        
