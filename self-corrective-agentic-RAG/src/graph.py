import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src import workarounds
workarounds.monkey_patch()

from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from src.nodes import (
    AgentState, retrieve_from_vectorstore, retrieve_from_knowledge_graph, grade_documents, generate, 
    rewrite_query, web_search, decide_to_generate
)

memory = InMemorySaver()

graph = StateGraph(AgentState)

graph.add_node('retrieve_from_vectorstore', retrieve_from_vectorstore)
graph.add_node('retrieve_from_knowledge_graph', retrieve_from_knowledge_graph)
graph.add_node('grade_documents', grade_documents)
graph.add_node('generate', generate)
graph.add_node('transform_query', rewrite_query)
graph.add_node('web_search', web_search)

graph.add_edge(START, 'retrieve_from_vectorstore')
graph.add_edge(START, 'retrieve_from_knowledge_graph')
graph.add_edge('retrieve_from_vectorstore', 'grade_documents')
graph.add_edge('retrieve_from_knowledge_graph', 'grade_documents')
graph.add_conditional_edges(
    source='grade_documents',
    path=decide_to_generate,
    path_map={
        'transform_query': 'transform_query',
        'generate': 'generate'
    }
)

graph.add_edge('transform_query', 'web_search')
graph.add_edge('web_search', 'generate')
graph.add_edge('generate', END)

agent = graph.compile(checkpointer=memory)


def interact_with_agent(
    query: str,
    thread_id: str
):
    
    config = {'configurable': {'thread_id': thread_id}}
    # response = agent.invoke(
    #     {
    #         'question': query
    #     },
    #     config=config
    # )
    
    #for debugging -> will be removed once app is built    
    for output in agent.stream({'question': query}, config=config):
        for k, v in output.items():
            print(f'Node: {k}')
        print('\n---\n')
        

    print(v['generation'])
    # return response['generation']
    
    
if __name__ == '__main__':
    interact_with_agent(query="Apple Intelligence", thread_id='1')