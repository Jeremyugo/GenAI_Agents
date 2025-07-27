import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from typing import Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langgraph.graph import StateGraph, END
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver

from utils.helper_functions import postgres_connection_string
from utils.config import ENV_FILE_PATH
from src.prompts import check_query_system_prompt, generate_query_system_prompt

load_dotenv(ENV_FILE_PATH)

memory = InMemorySaver()
langchain_db = SQLDatabase.from_uri(
    database_uri=postgres_connection_string('chinook')
)


function_registry = []

def register_function(func):
    function_registry.append(func)
    
    return func


llm = ChatOpenAI(model='gpt-3.5-turbo')

toolkit = SQLDatabaseToolkit(db=langchain_db, llm=llm)
sql_tools = toolkit.get_tools()


# Tools
@register_function
@tool
def list_tables(state: MessagesState):
    """Returns a comma-separated list of tables in the database"""
    
    list_tables_tool = next(tool for tool in sql_tools if tool.name == 'sql_db_list_tables')
    tool_message = list_tables_tool.invoke('')
    
    return tool_message


@register_function
@tool
def get_schema(
        list_of_tables: Annotated[str, 'comma-separated list of tables relevant to the input query']
    ):
    """Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables."""
    
    get_schema_tool = next(tool for tool in sql_tools if tool.name == 'sql_db_schema')
    tool_message = get_schema_tool.invoke(list_of_tables)
    
    return tool_message


@register_function
@tool
def verify_query(
        generated_sql_query: Annotated[str, 'Generated SQL query to be verfied']
    ):
    """Verifies the Generated SQL BEFORE executing it"""   
    
    system_prompt = check_query_system_prompt(dialect=langchain_db.dialect)
    content = f"{system_prompt}\n\n{generated_sql_query}"
    check_query_tool = next(tool for tool in sql_tools if tool.name == 'sql_db_query_checker')
    tool_message = check_query_tool.invoke(content)
    
    return tool_message


@register_function
@tool
def execute_verified_query(
        sql_query_to_execute: Annotated[str, 'This is the detailed and verified SQL query to executed']
    ):
    """Execute the SQL Query AFTER verifying it with the `verify_query` tool."""
    
    execute_query_tool = next(tool for tool in sql_tools if tool.name == 'sql_db_query')
    tool_message = execute_query_tool.invoke(sql_query_to_execute)
    
    return tool_message


tools = [f for f in function_registry]
llm_with_tools = llm.bind_tools(tools)


def generate_query(state: MessagesState):
    """Generates the SQL query to be executed"""
    system_prompt = SystemMessage(
        content=generate_query_system_prompt(dialect=langchain_db, top_k=5)
    )
    response = llm_with_tools.invoke([system_prompt] + state['messages'])
    
    return {'messages': [response]}


def should_continue(state: MessagesState) -> str:
    last_message = state['messages'][-1]
    if not last_message.tool_calls:
        return 'end'
    else:
        return 'continue'
    

# Build Graph
graph_builder = StateGraph(MessagesState)
tools_node = ToolNode(tools=tools)

graph_builder.add_node('generate_query', generate_query)
graph_builder.set_entry_point('generate_query')
graph_builder.add_node('tools', tools_node)
graph_builder.add_conditional_edges(
    source='generate_query',
    path=should_continue,
    path_map={
        'end': END,
        'continue': 'tools'
    }
)
graph_builder.add_edge('tools', 'generate_query')

graph = graph_builder.compile(checkpointer=memory)

    

def interact_with_agent(
    query: str,
    session_id: str
):
    config = {'configurable': {'thread_id': session_id}}
    response = graph.invoke(
        {
            'messages': [
                {
                    'role': 'user',
                    'content': query
                }
            ]
        },
        config=config
    )
    
    return response['messages'][-1].content
