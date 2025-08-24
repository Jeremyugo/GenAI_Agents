import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src import workarounds
workarounds.monkey_patch()

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver

from src.nodes import (
    AgentState, retrieve_from_all_sources, generate_query_or_respond, grade_documents,
    generate_response, rewrite_query, web_search, decide_to_generate,
)

memory = InMemorySaver()


def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node(generate_query_or_respond)
    graph.add_node('retrieve_from_all_sources', ToolNode(tools=[retrieve_from_all_sources]))
    graph.add_node('grade_documents', grade_documents)
    graph.add_node('generate_response', generate_response)
    graph.add_node('transform_query', rewrite_query)
    graph.add_node('web_search', web_search)

    graph.set_entry_point('generate_query_or_respond')

    graph.add_conditional_edges(
        source='generate_query_or_respond',
        path=tools_condition,
        path_map={
            'tools': 'retrieve_from_all_sources',
            END: END
        }
    )

    graph.add_edge('retrieve_from_all_sources', 'grade_documents')
    graph.add_conditional_edges(
        source='grade_documents',
        path=decide_to_generate,
        path_map={
            'transform_query': 'transform_query',
            'generate': 'generate_response'
        }
    )

    graph.add_edge('transform_query', 'web_search')
    graph.add_edge('web_search', 'generate_response')
    graph.add_edge('generate_response', END)

    agent = graph.compile(checkpointer=memory)
    
    return agent


agent = build_agent()

async def interact_with_agent(
    query: str,
    thread_id: str,
    agent = agent
):
    config = {'configurable': {'thread_id': thread_id}}

    # Include history in the agent's input
    response = await agent.ainvoke(
        {
            'messages': query,
        },
        config=config
    )    
    
    return response['messages'][-1].content
    