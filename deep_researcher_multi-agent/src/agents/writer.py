import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.state import AgentState
from src.prompts import report_draft_prompt
from src.utils import BaseAgent

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI

import asyncio
from langgraph.graph import StateGraph, END


class WritingAgent(BaseAgent):
    def __init__(self, model_name: str = "gpt-4.1"):
        self.model = ChatOpenAI(model=model_name)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ('system', report_draft_prompt),
                ('human', "This is the research topic: \n\n{topic}, and the section data containing the section plan and sources: \n\n{section_data}")
            ]
        )
        
        self.chain = self.prompt | self.model


    async def write_section(self, topic: str, section_data: str) -> str:

        response = await self.chain.ainvoke(
            {
                'topic': topic,
                'section_data': section_data
            }
        )
        
        return response.content


    async def _agent_node(self, state: AgentState) -> dict:
        section_tasks = [
            self.write_section(
                topic=state['topic'],
                section_data=section_data
            )
            for section_data in state['writing_plan_and_sources']
        ]
        section_drafts = await asyncio.gather(*section_tasks)

        full_report = "\n\n".join(section_drafts)
        
        return {
            "full_report_draft": full_report,
        }


    def build_agent(self):
        graph = StateGraph(AgentState)
        graph.add_node("writing_agent", self._agent_node)
        
        graph.set_entry_point("writing_agent")
        graph.add_edge("writing_agent", END)
        
        return graph.compile()


    @classmethod
    def create_agent(cls, model_name: str = "gpt-4.1"):
        agent = cls(model_name=model_name).build_agent()
        
        return agent