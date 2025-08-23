import sys
import os
import re
import ast
import asyncio
import unicodedata
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.tools import BraveSearch
from langchain_community.document_loaders import WebBaseLoader
from langgraph.graph import StateGraph

from src.prompts import search_query_generation_prompt
from src.state import AgentState
from src.utils import BaseAgent


search_tool = BraveSearch.from_api_key(
    api_key=os.environ.get('BRAVE_SEARCH_API_KEY'),
    search_kwargs={'count': 3}
)


class SearchQuery(BaseModel):
    search_query: str = Field(
        description="Query for web search"
    )
    
class Queries(BaseModel):
    search_queries: list[SearchQuery] = Field(
        description="List of search queries"
    )
    
    
    
class ResearchAgent(BaseAgent):
    def __init__(
            self, 
            model_name: str = "gpt-4o", 
            number_of_queries: int = 3
        ):
        
        self.number_of_queries = number_of_queries
        self.model = ChatOpenAI(model=model_name)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ('system', search_query_generation_prompt),
                ('human', (
                        "This is the research topic: \n\n {topic} \n\n. "
                        "Please generate \n\n{number_of_queries} web search queries that will provide enough information " 
                        "needed to write this section of the report: \n\n {section} \n\n" 
                    )
                )
            ]
        )

        self.chain = self.prompt | self.model.with_structured_output(Queries)
    
    
    async def generate_sources(self, state: dict) -> list[str]:
        results = []
        for section in state['writing_plan']:
            web_search_queries = await self.chain.ainvoke(
                {
                    'number_of_queries': state['number_of_queries'],
                    'topic': state['topic'],
                    'section': section
                }
            )
        
            web_search_queries = [
                query.search_query for query in web_search_queries.search_queries
            ]
            
            brave_search_results = await self.brave_search_async(web_search_queries)
            formatted_sources = await self.deduplicate_and_format_sources(brave_search_results)
            
            results.append(f"Research Plan:\n\n{section}\n\n{formatted_sources}")

        return results
        
        
        
    def clean_text(self, text: str, max_tokens_per_source: int = 875) -> str:
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        text = re.sub(r'[^\x00-\x7F]+', '', text)        # Remove non-ASCII
        text = re.sub(r'\n+', '\n', text)                # Collapse multiple newlines
        text = re.sub(r'[ \t]+', ' ', text)              # Collapse spaces/tabs
        text = re.sub(r' *\n *', '\n', text)             # Trim space around newlines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = '\n'.join(lines)
        
        char_limit = max_tokens_per_source * 4
        raw_content = text or ""

        if len(raw_content) > char_limit:
            raw_content = raw_content[:char_limit] + "... [truncated]"
            raw_content = f"Full source content limited to {max_tokens_per_source} tokens: {raw_content}\n\n"
        
        return raw_content
    
    
    async def deduplicate_and_format_sources(self, search_results: list[str]) -> str:
        try:
            parsed_results = []
            for result in search_results:
                try:
                    if result and result != "[]":
                        parsed = ast.literal_eval(result)
                        parsed_results.append(parsed)
                except (ValueError, SyntaxError) as e:
                    print(f"Failed to parse search result: {e}")
                    continue
            
            if not parsed_results:
                return "No sources found"
                
            search_results = [item for sublist in parsed_results for item in sublist]
            
            if not search_results:
                return "No sources found after parsing"
                
            unique_sources = {web_result['link'] for web_result in search_results}
            docs = await self.load_all_fast(unique_sources)
            doc_lookup = {doc.metadata['source']: self.clean_text(doc.page_content) for doc in docs}
            
            formatted_text = "Sources: \n\n"
            for i, result in enumerate(search_results, 1):
                formatted_text += f"Source {i} - {result['title']}:\n===\n"
                formatted_text += f"URL: {result['link']}\n===\n"
                formatted_text += f"Most relevant content from source: {result['snippet']}\n===\n"
                formatted_text += doc_lookup.get(result['link'], 'No content available')
                
            return formatted_text
        except Exception as e:
            print(f"Error in deduplicate_and_format_sources: {e}")
            return "Error formatting sources"
    
    
    
    async def brave_search_async(self, queries: list[str]) -> list:
        async def search(query):
            while True:
                try:
                    result = await search_tool.ainvoke(query)
                    if result:
                        return result
                    await asyncio.sleep(0.5)
                except Exception as e:
                    if "429" in str(e):
                        await asyncio.sleep(0.5)
                    else:
                        print(f"Error searching for {query}: {e}")
                        return "[]"  

        results = await asyncio.gather(*[search(q) for q in queries])
        return results
    
    
    async def load_with_real_timeout(self, url: str, timeout: float = 2.0):
        try:
            return await asyncio.wait_for(asyncio.to_thread(WebBaseLoader(url).load), timeout)
        except (asyncio.TimeoutError, Exception):
            return []

    
    async def load_all_fast(self, urls: list[str]):
        tasks = [self.load_with_real_timeout(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return [doc for sublist in results for doc in sublist]
    

        
    async def _agent_node(self, state: AgentState) -> AgentState:
        separator = "-"*80
        sections = state['writing_plan'].split(separator)
        sections = [section.strip() for section in sections]
        print(f"Length of sections: {len(sections)}")
        
        generated_sources = await self.generate_sources(
            {
                'number_of_queries': self.number_of_queries,
                'topic': state['topic'],
                'writing_plan': sections
            }
        )
        
        return {
            'writing_plan_and_sources': generated_sources
        }
        
    
    def build_agent(self):
        graph_builder = StateGraph(AgentState)
        
        graph_builder.add_node('generate_sources', self._agent_node)
        graph_builder.set_entry_point('generate_sources')
        graph_builder.set_finish_point('generate_sources')
        
        query_agent = graph_builder.compile()
        
        return query_agent
    
    
    @classmethod
    def create_agent(
            cls, 
            model_name: str = "gpt-4o", 
            number_of_queries: int = 5,
        ):
        agent = cls(
                model_name=model_name,
                number_of_queries=number_of_queries,
            )
        return agent.build_agent()