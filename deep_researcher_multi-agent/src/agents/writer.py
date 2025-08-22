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
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model = ChatOpenAI(model=model_name)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ('system', report_draft_prompt),
                ('human', "This is the research topic: \n\n{topic}, and the section data containing the section plan and sources: \n\n{section_data}")
            ]
        )
        
        self.chain = self.prompt | self.model


    def extract_references_from_section(self, section_data: str) -> list:
        """Extract and format references from a section's source data"""
        references = []
        lines = section_data.split('\n')
        in_sources_section = False
        
        current_ref = {}
        for line in lines:
            if line.lower().startswith('sources:'):
                in_sources_section = True
                continue
                
            if in_sources_section:
                if line.startswith('Source ') and ' - ' in line:
                    if current_ref:  
                        references.append(current_ref)
                    ref_num = line.split(' ', 1)[1].split(' - ', 1)[0]
                    title = line.split(' - ', 1)[1].strip()
                    current_ref = {'number': ref_num, 'title': title}
                elif line.startswith('URL: '):
                    current_ref['url'] = line.split('URL: ')[1].strip()
                elif line.startswith('Most relevant content from source: '):
                    current_ref['content'] = line.split('Most relevant content from source: ')[1].strip()
        
        if current_ref:  
            references.append(current_ref)
        
        return references


    def format_references(self, all_references: list) -> str:
        """Format references in IEEE style"""
        seen = set()
        unique_refs = []
        for ref in all_references:
            ref_key = (ref.get('title', ''), ref.get('url', ''))
            if ref_key not in seen:
                seen.add(ref_key)
                unique_refs.append(ref)
        
        references_section = "References\n\n"
        for i, ref in enumerate(unique_refs, 1):
            title = ref.get('title', 'No title available')
            url = ref.get('url', 'No URL available')
            references_section += f"[{i}] {title}. Available: {url}\n\n"
        
        return references_section


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
        
        all_references = []
        for section_data in state['writing_plan_and_sources']:
            section_refs = self.extract_references_from_section(section_data)
            all_references.extend(section_refs)
        
        references_section = self.format_references(all_references)

        full_report = "\n\n".join(section_drafts) + "\n\n" + references_section
        
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
    def create_agent(cls, model_name: str = "gpt-4o-mini"):
        agent = cls(model_name=model_name).build_agent()
        
        return agent