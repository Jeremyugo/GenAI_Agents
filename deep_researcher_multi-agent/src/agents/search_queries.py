import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.prompts import search_query_generation_prompt
from src.state import AgentState
from src.utils import BaseAgent

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from langgraph.graph import StateGraph


class SearchQuery(BaseModel):
    search_query: str = Field(
        description="Query for web search"
    )
    
class Queries(BaseModel):
    search_queries: list[SearchQuery] = Field(
        description="List of search queries"
    )
    

class SearchQueryAgent(BaseAgent):
    def __init__(self, model_name: str = "gpt-4o", number_of_queries: int = 3):
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
            {'number_of_queries': input_dict['number_of_queries'],
            'topic': input_dict['topic'],
            'research_plan': plan_item}
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
            query.search_query for result in generated_search_queries for query in result.search_queries
        ]
        
        return {
            'search_queries': generated_search_queries
        }
    
    
    def build_agent(self,):
        graph_builder = StateGraph(AgentState)
        
        graph_builder.set_node('search_query', self._agent_node)
        graph_builder.set_entry_point('search_query')
        graph_builder.set_finish_point('search_query')
        
        query_agent = graph_builder.compile()
        
        return query_agent
    
    
    @classmethod
    def create_agent(cls, model_name: str = "gpt-4o"):
        agent = cls(model_name=model_name)
        return agent.build__agent()