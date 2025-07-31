import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import asyncio
from src import workarounds
workarounds.monkey_patch()

from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from src.nodes import (
    AgentState, retrieve_from_all_sources, grade_documents, generate_conversational_response, 
    generate_rag_response, rewrite_query, web_search, decide_to_generate, classify_query
)

memory = InMemorySaver()

graph = StateGraph(AgentState)

graph.add_node('retrieve_from_all_sources', retrieve_from_all_sources)
graph.add_node('grade_documents', grade_documents)
graph.add_node('generate_rag_response', generate_rag_response)
graph.add_node('generate_conversational_response', generate_conversational_response)
graph.add_node('transform_query', rewrite_query)
graph.add_node('web_search', web_search)

graph.add_conditional_edges(
    source=START,
    path=classify_query,
    path_map={
        'conversational': 'generate_conversational_response',
        'informational': 'retrieve_from_all_sources'
    }
)

graph.add_edge('retrieve_from_all_sources', 'grade_documents')
graph.add_conditional_edges(
    source='grade_documents',
    path=decide_to_generate,
    path_map={
        'transform_query': 'transform_query',
        'generate': 'generate_rag_response'
    }
)

graph.add_edge('transform_query', 'web_search')
graph.add_edge('web_search', 'generate_rag_response')
graph.add_edge('generate_rag_response', END)
graph.add_edge('generate_conversational_response', END)

agent = graph.compile(checkpointer=memory)


async def interact_with_agent(
    query: str,
    thread_id: str,
    history: list
):
    config = {'configurable': {'thread_id': thread_id}}

    # Include history in the agent's input
    response = await agent.ainvoke(
        {
            'question': query,
            'history': history
        },
        config=config
    )

    return response['generation']
    
    
if __name__ == '__main__':
    asyncio.run(interact_with_agent(query="Hi my name is Jerry!", thread_id='1'))