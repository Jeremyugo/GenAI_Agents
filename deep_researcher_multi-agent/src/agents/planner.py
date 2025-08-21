import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.state import AgentState
from src.prompts import research_planner_system_prompt, writing_planner_prompt
from src.utils import BaseAgent

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser



class PlanningAgent(BaseAgent):
    def __init__(self, model_name: str = "gpt-4o"):
        self.model = ChatOpenAI(model=model_name)
        self.research_plan_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", research_planner_system_prompt),
                ('human', "Here is the research topic: \n\n{topic}. Generate a research plan to explore the topic"),
            ]
        )
        self.writing_plan_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', writing_planner_prompt),
                ('human', "Here is the research topic: \n\n{topic} and research plan: \n\n{research_plan}. Create well-organized sections.")
            ]
        )
        
        self.research_plan_chain = self.research_plan_prompt | self.model | StrOutputParser()
        self.writing_plan_chain = self.writing_plan_prompt | self.model | StrOutputParser()
          
    
    def _agent_node(self, state: AgentState) -> AgentState:
        messages = state['messages']
        writing_plan_feedback = state.get('writing_plan_feedback', '')
        
        research_plan = self.research_plan_chain.invoke(
            {
                'topic': messages
            }
        )
        
        writing_plan = self.writing_plan_chain.invoke(
            {
                'topic': messages,
                'research_plan': research_plan,
                'writing_plan_feedback': writing_plan_feedback
            }
        )
        
        return {
            'research_plan': research_plan,
            'writing_plan': writing_plan
        }
        

    
    
    def build_agent(self,):
        graph_builder = StateGraph(AgentState)

        graph_builder.add_node('planning_agent', self._agent_node)
        graph_builder.set_entry_point('planning_agent')
        graph_builder.set_finish_point('planning_agent')

        planner_agent = graph_builder.compile()
        
        return planner_agent
    
        
    @classmethod
    def create_agent(cls, model_name: str = "gpt-4o"):
        agent = cls(model_name=model_name)
        return agent.build_agent()
        
