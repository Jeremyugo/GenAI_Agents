import os
import sys
import ast
from pathlib import Path
from typing import List, TypedDict, Annotated
import asyncio

sys.path.append(str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_community.tools import BraveSearch
from langchain_openai import ChatOpenAI
from langchain.schema import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import ToolMessage, AIMessage
from langgraph.graph import MessagesState
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState

from src.vector import create_vector_retriever
from src.knowledge_graph import search_knowledge_graph
from src.prompt import grade_prompt, generate_prompt, re_write_prompt, question_extraction_prompt, tool_description
from utils.config import ENV_FILE_PATH

load_dotenv(ENV_FILE_PATH)

llm_4o_mini = ChatOpenAI(model='gpt-3.5-turbo')
llm_4o_mini = ChatOpenAI(model='gpt-4o-mini')


class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )


# grader llm chain
structured_llm_grader = llm_4o_mini.with_structured_output(GradeDocuments)
retrieval_grader = grade_prompt | structured_llm_grader

# answer generation llm chain
rag_chain = generate_prompt | llm_4o_mini | StrOutputParser()

# rewrite user query llm chain
question_rewriter = re_write_prompt | llm_4o_mini |StrOutputParser()

# conversational llm chain
conversational_chain = llm_4o_mini | StrOutputParser()

# web search tool (Brave Search)
web_search_tool = BraveSearch.from_api_key(
    api_key=os.environ.get('BRAVE_SEARCH_API_KEY'),
    search_kwargs={'count': 3}
)


class AgentState(MessagesState):
    """
    Represents the state of our graph.

    Attributes:
        user_question: question
        generation: LLM generation
        web_search: whether to add search
        documents_vs: list of documents from vectorstore
        documents_kg: list of documents from knowledge graph
        documents: list of all documents (vectorstore + knowledge graph)
    """
    
    user_question: str
    generation: str
    documents_vs: List[str]
    documents_kg: List[str]
    documents: List[str]
    web_search: str
 
    
def generate_query_or_respond(state: AgentState):
    """
        Call the model to generate a response based on the current state. Given
        the question, it will decide to retrieve using the
        retrieve_from_all_sources tool or simply respond to the user.
    """
    user_query = state['messages']
    
    model = llm_4o_mini.bind_tools([retrieve_from_all_sources])
    response = model.invoke(user_query)
    
    return {
        **state,
        'messages': [response]
    }


@tool(description=tool_description)
async def retrieve_from_all_sources(
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId] 
    ) -> Command:
    """
        Retrieve Documents from both the vectorstore and knowledge graph
        
        Args:
            state (dict): The current graph state
        
        Returns:
            state (dict): New 'documents_vs' and 'documents_kg' keys added to state, that contains the retrieved documents
    """
    
    question_extraction_chain = question_extraction_prompt | llm_4o_mini | StrOutputParser()
    message = state['messages'][-2]
    question = question_extraction_chain.invoke(message)

    compression_retriever = create_vector_retriever()

    documents_vs, documents_kg = await asyncio.gather(
        asyncio.to_thread(compression_retriever.invoke, question),
        search_knowledge_graph(query=question, limit=5)
    )
    
    return Command(
        update={
            'user_question': question,
            "documents_vs": documents_vs,
            "documents_kg": documents_kg,
            "messages": [
                ToolMessage(f"Updated the documents key", tool_call_id=tool_call_id)
            ]
        }
    )


def grade_documents(state: AgentState) -> AgentState:
    """
        Determines whether the retrieved documents are relevant to the question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with only filtered relevant documents
    """
    
    documents_vs = state['documents_vs']
    documents_kg = state['documents_kg']
    question = state['user_question']
    
    documents = documents_vs + documents_kg
    
    filtered_docs = []
    web_search = 'No'
    
    for doc in documents:
        score = retrieval_grader.invoke(
            {
                'user_question': question,
                'document': doc
            }
        )
        
        grade = score.binary_score
        if grade == 'yes':
            filtered_docs.append(doc)
        else:
            web_search = 'Yes'
            continue
    
    return {
        'documents': filtered_docs,
        'web_search': web_search
    }


def generate_response(state: AgentState) -> AgentState:
    """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
    """
    
    question = state['user_question']
    documents = state['documents']

    generation = rag_chain.invoke(
        {
            'user_question': question,
            'context': documents,
        }
    )
    
    generation = [AIMessage(content=generation)]
    
    return {
        'messages': state['messages'] + generation
    }


def rewrite_query(state: AgentState) -> AgentState:
    """
        Transform the query to produce a better question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates question key with a re-phrased question
    """
    
    question = state['user_question']
    documents = state['documents']
    
    question_rewriter.invoke({'user_question': question})
    
    return {
        'user_question': question,
        'documents': documents
    }
    

def web_search(state: AgentState) -> AgentState:
    """
        Web search based on the re-phrased question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with appended web results
    """
    
    question = state['user_question']
    documents = state['documents']
    docs = web_search_tool.invoke(
        {
            'query': question
        }
    )

    web_results = "\n".join([result['snippet'] for result in ast.literal_eval(docs)])
    web_results = Document(page_content=web_results)
    documents.append(web_results)
    
    return {
        'user_question': question,
        'documents': documents
    }
    

def decide_to_generate(state: AgentState) -> AgentState:
    """
        Determines whether to generate an answer, or re-generate a question.

        Args:
            state (dict): The current graph state

        Returns:
            str: Binary decision for next node to call
    """
    
    web_search = state['web_search']
    
    if web_search == 'Yes':
        print(
            'ALL DOCUMENTS ARE NOT RELEVANT TO THE QUESTION, TRANSFORM QUERY...'
        )
        return 'transform_query'
    
    else:
        print(
            'GENERATE...'
        )
        return 'generate'

