import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.state import AgentState
from src.prompts import editor_system_prompt
from src.utils import BaseAgent

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph


class EditorAgent(BaseAgent):
    def __init__(self, model_name: str = "gpt-4o"):
        self.model = ChatOpenAI(model=model_name)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ('system', editor_system_prompt),
                ('human', "This is the research topic: \n\n{topic}, and the report draft: \n\n{report_draft}. Please edit it.")
            ]
        )
        
        self.chain = self.prompt | self.model | StrOutputParser()
        
        
    def _agent_node(self, state: AgentState) -> AgentState:
        topic = state['topic']
        report_draft = state['full_report_draft']
        
        final_report = self.chain.invoke(
            {
                'topic': topic,
                'report_draft': report_draft
            }
        )
        
        return {
            'final_report': final_report
        }
        
        
    def build_agent(self,):
        graph_builder = StateGraph(AgentState)
        
        graph_builder.add_node('editor_agent', self._agent_node)
        graph_builder.set_entry_point('editor_agent')
        graph_builder.set_finish_point('editor_agent')
        
        editor_agent = graph_builder.compile()
        
        return editor_agent
    

    @classmethod
    def create_agent(cls, model_name: str = "gpt-4o"):
        agent = cls(model_name=model_name)
        return agent.build_agent()