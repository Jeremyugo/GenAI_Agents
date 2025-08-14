import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import ast
import asyncio

from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_community.tools import BraveSearch
from langchain_community.document_loaders import WebBaseLoader
from langgraph.graph import StateGraph

from src.prompts import search_query_generation_prompt
from src.state import AgentState
from src.utils import BaseAgent



search_tool = BraveSearch.from_api_key(
    api_key=os.environ.get('BRAVE_SEARCH_API_KEY'),
    search_kwargs={'count': 5}
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
            number_of_queries: int = 3,
            load_full_page_content: bool = False
        ):
        
        self.load_full_page_content = load_full_page_content
        self.number_of_queries = number_of_queries
        self.model = ChatOpenAI(model=model_name)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ('system', search_query_generation_prompt),
                ('human', "Search topic: \n\n {topic} \n\n Research Plan: \n\n {research_plan} \n\n Number of queries: \n\n{number_of_queries}")
            ]
        )

        self.chain = self.prompt | self.model.with_structured_output(Queries)
    
    
    def generate_batch_queries(self, input_dict):
        return self.chain.batch([
            {
                'number_of_queries': input_dict['number_of_queries'],
                'topic': input_dict['topic'],
                'research_plan': plan_item
            }
            for plan_item in input_dict['research_plan_items']
        ])
    
    
    def _agent_node(self, state: AgentState):
        generate_search_queries = RunnableLambda(self.generate_batch_queries)
        generated_search_queries = generate_search_queries.invoke(
            {
                'number_of_queries': self.number_of_queries,
                'topic': state['messages'],
                'research_plan_items': state['todos']
            }
        )
        
        generated_search_queries = [
            query.search_query 
            for result in generated_search_queries 
            for query in result.search_queries
        ]
        
        return {
            'search_queries': generated_search_queries
        }
    
    
    
    async def brave_search_async(self, queries: list[str]) -> list:
        async def search(query):
            while True:
                try:
                    return await search_tool.ainvoke(query)
                except Exception as e:
                    if "429" in str(e):
                        await asyncio.sleep(0.5)
                    else:
                        raise
        return [await search(q) or await asyncio.sleep(0.5) for q in queries]
    
    
    async def load_with_real_timeout(self, url: str, timeout: float = 2.0):
        try:
            return await asyncio.wait_for(asyncio.to_thread(WebBaseLoader(url).load), timeout)
        except (asyncio.TimeoutError, Exception):
            return []


    async def load_all_fast(self, urls: list[str]):
        results = []
        for url in urls:
            docs = await self.load_with_real_timeout(url)
            results.extend(docs)
        return results


    async def deduplicate_and_load_page_content(self, search_results: list[str]):
        search_results = [ast.literal_eval(result) for result in search_results]
        search_results = [item for sublist in search_results for item in sublist]
        
        if self.load_full_page_content:
            unique_links = []
            
            for web_result in search_results:
                if web_result['link'] not in unique_links:
                    unique_links.append(web_result['link'])
                    
            docs = await self.load_all_fast(unique_links)
            return docs
        
        return search_results
    
    
    async def perform_web_research(self, state: AgentState):
        
        generated_search_queries = state['search_queries']
        
        brave_search_results = await self.brave_search_async(generated_search_queries)
        brave_search_results = await self.deduplicate_and_load_page_content(search_results=brave_search_results)
        
        return {
            'search_results': brave_search_results
        }

    
    def build_agent(self,):
        graph_builder = StateGraph(AgentState)
        
        graph_builder.add_node('search_query', self._agent_node)
        graph_builder.add_node('web_search', self.perform_web_research)
        graph_builder.add_edge('search_query', 'web_search')
        
        graph_builder.set_entry_point('search_query')
        graph_builder.set_finish_point('web_search')
        
        query_agent = graph_builder.compile()
        
        return query_agent
    
    
    @classmethod
    def create_agent(
            cls, 
            model_name: str = "gpt-4o", 
            number_of_queries: int = 3,
            load_full_page_content: bool = False
        ):
        agent = cls(
                model_name=model_name,
                number_of_queries=number_of_queries,
                load_full_page_content=load_full_page_content
            )
        return agent.build_agent()