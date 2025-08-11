import os
import sys
import ast
from pathlib import Path
from typing import List, TypedDict
import asyncio

sys.path.append(str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_community.tools import BraveSearch
from langchain_openai import ChatOpenAI
from langchain.schema import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage
from langgraph.graph import MessagesState

from src.vector import create_vector_retriever
from src.knowledge_graph import search_knowledge_graph
from src.prompt import grade_prompt, generate_prompt, re_write_prompt, query_classifier_prompt
from utils.config import ENV_FILE_PATH

load_dotenv(ENV_FILE_PATH)

llm_gpt3_5 = ChatOpenAI(model='gpt-3.5-turbo')
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
rag_chain = generate_prompt | llm_gpt3_5 | StrOutputParser()

# rewrite user query llm chain
question_rewriter = re_write_prompt | llm_gpt3_5 |StrOutputParser()

# conversational llm chain
conversational_chain = llm_gpt3_5 | StrOutputParser()

# web search tool (Brave Search)
web_search_tool = BraveSearch.from_api_key(
    api_key=os.environ.get('BRAVE_SEARCH_API_KEY'),
    search_kwargs={'count': 3}
)


class AgentState(MessagesState):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        web_search: whether to add search
        documents_vs: list of documents from vectorstore
        documents_kg: list of documents from knowledge graph
        documents: list of all documents (vectorstore + knowledge graph)
    """
    
    question: str
    generation: str
    documents_vs: List[str]
    documents_kg: List[str]
    documents: List[str]
    web_search: str


def extract_core_question(message: str) -> str:
    system_prompt = (
        "You are an assistant that extracts the question from a user message for document retrieval"
        "Return only the question text without extra commentary"
    )
    
    result = llm_gpt3_5.invoke([
        HumanMessage(content=system_prompt),
        HumanMessage(content=message)
    ])
    
    return result.content.strip()



def classify_query(state: AgentState) -> AgentState:
    """
        Classify the query into either 'conversational' or 'informational'.
        If the query relates to Apple Inc./Siri, Artificial Intelligence, or Competitor Analysis/Market research
        then its 'informational' otherwise its 'coonversational'

        Args:
            query (str): The user query to classify.

        Returns:
            str: The classification result.
    """
    
    user_query = state['messages'][-1].content
    query_classifier = query_classifier_prompt | llm_gpt3_5 | StrOutputParser()
    classification = query_classifier.invoke({'query': user_query})

    if 'conversational' in classification.lower():
        return 'conversational'
    else:
        return 'informational'

    
# DEPRECATED: This function is no longer used in the current graph flow.   
def retrieve_from_vectorstore(state: AgentState) -> AgentState:
    """
        Retrieve Documents from the Qdrant vectorstore
        
        Args:
            state (dict): The current graph state
        
        Returns:
            state (dict): New 'documents_vs' key added to state, that contains the retrieved documents
    """
    
    question = state['question']
    
    compression_retriever = create_vector_retriever()
    documents_vs = compression_retriever.invoke(question)
    
    return {
        'documents_vs': documents_vs
    }


# DEPRECATED: This function is no longer used in the current graph flow.
async def retrieve_from_knowledge_graph(state: AgentState) -> AgentState:
    """
        Retrieve Documents from the Knowledge Graph
        
        Args:
            state (dict): The current graph state
        
        Returns:
            state (dict): New 'documents_kg' key added to state, that contains the retrieved documents
    """
    
    question = state['question']
    
    documents_kg = await search_knowledge_graph(
        query=question,
        limit=3
    )
    
    return {
        'documents_kg': documents_kg
    }


async def retrieve_from_all_sources(state: AgentState) -> AgentState:
    """
        Retrieve Documents from both the vectorstore and knowledge graph
        
        Args:
            state (dict): The current graph state
        
        Returns:
            state (dict): New 'documents_vs' and 'documents_kg' keys added to state, that contains the retrieved documents
    """
    
    question = extract_core_question(
        message=state['messages'][-1].content
    )
    print(f"Formulated question: {question}\n\n")

    compression_retriever = create_vector_retriever()

    documents_vs, documents_kg = await asyncio.gather(
        asyncio.to_thread(compression_retriever.invoke, question),
        search_knowledge_graph(query=question, limit=5)
    )
    
    return {
        'question': question,
        'documents_vs': documents_vs,
        'documents_kg': documents_kg
    }


def grade_documents(state: AgentState) -> AgentState:
    """
        Determines whether the retrieved documents are relevant to the question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with only filtered relevant documents
    """
    
    question = state['question']
    documents_vs = state['documents_vs']
    documents_kg = state['documents_kg']
    
    documents = documents_vs + documents_kg
    
    filtered_docs = []
    web_search = 'No'
    
    for doc in documents:
        score = retrieval_grader.invoke(
            {
                'question': question,
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
        'question': question,
        'documents': filtered_docs,
        'web_search': web_search
    }


def generate_rag_response(state: AgentState) -> AgentState:
    """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
    """
    
    question = state['question']
    documents = state['documents']

    generation = rag_chain.invoke(
        {
            'question': question,
            'context': documents,
        }
    )
    
    return {
        'question': question,
        'documents': documents,
        'generation': generation,
    }


def generate_conversational_response(state: AgentState) -> AgentState:
    """
        Generate conversational response

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
    """
    
    user_query = state['messages']

    generation = conversational_chain.invoke(user_query)

    return {
        'generation': generation,
    }


def rewrite_query(state: AgentState) -> AgentState:
    """
        Transform the query to produce a better question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates question key with a re-phrased question
    """
    
    question = state['question']
    documents = state['documents']
    
    question_rewriter.invoke({'question': question})
    
    return {
        'question': question,
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
    
    question = state['question']
    documents = state['documents']
    print(f"Web search for question: {question}")
    docs = web_search_tool.invoke(
        {
            'query': question
        }
    )

    web_results = "\n".join([result['snippet'] for result in ast.literal_eval(docs)])
    web_results = Document(page_content=web_results)
    documents.append(web_results)
    
    return {
        'question': question,
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

