import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import re
from collections import defaultdict
from typing import List, Dict, Optional

from src.state import AgentState
from src.prompts import writing_planner_prompt, main_section_prompt, subsection_prompt
from src.utils import BaseAgent

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI



class WritingAgent(BaseAgent):
    def __init__(self, model_name: str = "gpt-4o"):
        self.model = ChatOpenAI(model=model_name)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ('system', writing_planner_prompt),
                ('human', "Here is the Research topic \n\n {topic} \n\n and the research queries: \n\n {queries}")
            ]
        )
        
        self.chain = self.prompt | self.model | StrOutputParser()

    
    def split_into_sections(self, research_plan: str) -> List[Dict[str, str]]:
        """
        Parse a numbered plan like:
        1. **Title**  Description...
        1.1. **Sub Title** — Description...
        Returns: [{"title": "1. Title", "description": [...], "subsections": [{"title": "1.1. Sub", ...}, ...]}, ...]
        """
        sections: List[Dict[str, object]] = []
        current_main: Optional[Dict[str, object]] = None

        # Dash matcher: optional em/en/hyphen after subsection title
        dash_opt = r'(?:[\u2014\u2013-]\s*)?'  # — or – or -

        for raw in research_plan.splitlines():
            line = raw.strip()
            if not line:
                continue

            # Main section: 1. **Title** [desc...]
            m_main = re.match(r'^(\d+)\.\s+\*\*(.+?)\*\*\s*(.*)$', line)
            if m_main:
                # push previous main
                if current_main:
                    sections.append(current_main)
                num = m_main.group(1).strip()
                title_txt = m_main.group(2).strip()
                desc_txt = m_main.group(3).strip()
                current_main = {
                    "title": f"{num}. {title_txt}",
                    "description": [desc_txt] if desc_txt else [],
                    "subsections": []
                }
                continue

            # Subsection: 1.1. **Title** — desc...
            m_sub = re.match(rf'^(\d+\.\d+)\.\s+\*\*(.+?)\*\*\s*{dash_opt}(.*)$', line)
            if m_sub and current_main:
                sub_num = m_sub.group(1).strip()
                sub_title = m_sub.group(2).strip()
                sub_desc = m_sub.group(3).strip()
                current_main["subsections"].append({
                    "title": f"{sub_num}. {sub_title}",
                    "description": [sub_desc] if sub_desc else []
                })
                continue

            # Continuation lines → to last subsection if exists, else to main description
            if current_main:
                if current_main["subsections"]:
                    last_sub = current_main["subsections"][-1]
                    if last_sub["description"]:
                        last_sub["description"][-1] += " " + line
                    else:
                        last_sub["description"].append(line)
                else:
                    if current_main["description"]:
                        current_main["description"][-1] += " " + line
                    else:
                        current_main["description"].append(line)

        if current_main:
            sections.append(current_main)

        # Cast for type checkers
        return sections  # type: ignore[return-value]
    
    
    def generate_writing_plan(self, state: AgentState):
        writing_plan = self.chain.invoke(
            {
                'topic': state['messages'],
                'queries': state['search_queries']
            }
        )
        
        writing_plan = self.split_into_sections(writing_plan)
        
        return {
            'writing_plan': writing_plan
        }
  
  
    def text_similarity(self, query: str, text: str) -> float:
        """Calculate simple text similarity score (0-1)"""
        query_words = set(re.findall(r'\w+', query.lower()))
        text_words = set(re.findall(r'\w+', text.lower()))
        common = query_words & text_words
        return len(common) / len(query_words) if query_words else 0
  
  
    def get_relevant_sources(self, search_results: List[Dict], query: str, top_n: int = 3) -> List[Dict]:
        """Retrieve relevant sources based on query"""
        query = query.strip()
        if not query:
            return []
        
        scored_sources = []
        for source in search_results:
            title_score = self.text_similarity(query, source.get('title', ''))
            snippet_score = self.text_similarity(query, source.get('snippet', ''))
            
            total_score = (title_score * 0.7) + (snippet_score * 0.3)
            if total_score > 0:
                source_copy = source.copy()
                
                scored_sources.append((total_score, source_copy))
        
        scored_sources.sort(key=lambda x: x[0], reverse=True)
        return [source for _, source in scored_sources[:top_n]]
    
    
    def format_sources(self, sources: List[Dict]) -> str:
        """Format sources for inclusion in prompts"""
        if not sources:
            return "No specific sources provided. Use general knowledge with proper citation if needed."
        
        formatted = "Research Sources for this section:\n"
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'Untitled Source')
            url = source.get('link', '#')
            snippet = source.get('snippet', '')
            content = source.get('page_content', '')
            
            content_preview = ""
            if content:
                content_preview = (content[:400] + '...') if len(content) > 400 else content
            elif snippet:
                content_preview = snippet
            
            formatted += f"{i}. [{title}]({url})\n"
            if content_preview:
                formatted += f"   Content Preview: {content_preview}\n\n"
        
        return formatted
    
    
    async def generate_report_draft(self, state: AgentState):
        """
        Coordinates the writing process with source integration
        """
        
        sections = state['writing_plan']
        search_results = state['search_results']
        
        main_section_chain = (
            {"title": RunnablePassthrough(),
            "description": RunnablePassthrough(),
            "subsections": RunnablePassthrough(),
            "topic": RunnablePassthrough(),
            "sources": RunnablePassthrough()}
            | ChatPromptTemplate.from_template(main_section_prompt)
            | self.model
            | StrOutputParser()
        )
        
        subsection_chain = (
            {"parent_title": RunnablePassthrough(),
            "title": RunnablePassthrough(),
            "description": RunnablePassthrough(),
            "topic": RunnablePassthrough(),
            "sources": RunnablePassthrough()}
            | ChatPromptTemplate.from_template(subsection_prompt)
            | self.model
            | StrOutputParser()
        )
        
        report_content = {}
        full_report = []
        all_sources = defaultdict(list)
        source_counter = 1
        
        for section in sections:
            section_query = f"{section['title']}: {' '.join(section['description'])}"
            
            section_sources = self.get_relevant_sources(search_results=search_results, query=section_query)
            formatted_sources = self.format_sources(sources=section_sources)
            
            for src in section_sources:
                src_key = (src.get('title'), src.get('link'))
                if src_key not in all_sources:
                    all_sources[src_key] = source_counter
                    source_counter += 1
                    
            
            main_content = await main_section_chain.ainvoke({
                "title": f"{section['title']}",
                "description": "\n".join(section['description']),
                "subsections": [sub['title'] for sub in section['subsections']],
                "topic": state['messages'],
                "sources": formatted_sources
            })
            
            report_content[section['title']] = {
                'main_content': main_content,
                'subsections': {}
            }
            
            subsection_contents = []
            for subsection in section['subsections']:
                sub_query = f"{section['title']} {subsection['title']} {' '.join(subsection['description'])}"

                sub_sources = self.get_relevant_sources(search_results=search_results, query=sub_query)
                formatted_sub_sources = self.format_sources(sources=sub_sources)
                
                for src in sub_sources:
                    src_key = (src.get('title'), src.get('link'))
                    if src_key not in all_sources:
                        all_sources[src_key] = source_counter
                        source_counter += 1
                        
                
                sub_content = await subsection_chain.ainvoke({
                    "parent_title": section["title"],
                    "title": subsection["title"],
                    "description": "\n".join(subsection["description"]),
                    "topic": state['messages'],
                    "sources": formatted_sub_sources
                })
                
                report_content[section["title"]]["subsections"][subsection["title"]] = sub_content
                subsection_contents.append(f"### {subsection['title']}\n\n{sub_content}")
            
            full_section = f"## {section['title']}\n\n{main_content}"
            if subsection_contents:
                full_section += "\n\n" + "\n\n".join(subsection_contents)
            
            full_report.append(full_section)
        
        bibliography = "## References\n\n"
        for (title, url), idx in sorted(all_sources.items(), key=lambda x: x[1]):
            bibliography += f"{idx}. [{title}]({url})\n"
        
        full_report.append(bibliography)
        
        return {
            'full_report_draft': "\n\n".join(full_report)
        }
        
        
    def build_agent(self):
        graph_builder = StateGraph(AgentState)
        
        graph_builder.add_node('writing_plan', self.generate_writing_plan)
        graph_builder.add_node('draft_report', self.generate_report_draft)
        
        graph_builder.add_edge('writing_plan', 'draft_report')
        
        graph_builder.set_entry_point('writing_plan')
        graph_builder.set_finish_point('draft_report')
        
        writing_agent = graph_builder.compile()
        
        return writing_agent
    
    
    @classmethod
    def create_agent(cls, model_name: str = "gpt-4o"):
        agent = cls(model_name=model_name)
        return agent.build_agent()