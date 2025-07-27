from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import ChatMessagePromptTemplate, ChatPromptTemplate
from langgraph.graph import END, StateGraph, START
from langchain_community.tools import BraveSearch
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List, TypedDict
from src.vector import create_vectore_retriever
from src.prompt import grade_system_prompt, generate_system_prompt, re_write_system_prompt
from langchain.schema import Document
from langchain_core.output_parsers import StrOutputParser
from langchain import hub
import ast

compression_retriever = create_vectore_retriever()

llm_gpt3_5 = ChatOpenAI(model='gpt-3.5-turbo')
llm_4o_mini = ChatOpenAI(model='gpt-4o-mini')


class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""

    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )


# grader llm chain
structured_llm_grader = llm_gpt3_5.with_structured_output(GradeDocuments)
retrieval_grader = grade_system_prompt | structured_llm_grader

#


class AgentState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        web_search: whether to add search
        documents: list of documents
    """
    
    question: str
    generation: str
    documents: List[str]
    web_search: str
    
    
def retrieve(state: AgentState) -> AgentState:
    """
        Retrieve Documents from the Chromadb vectorstore
        
        Args:
            state (dict): The current graph state
        
        Returns:
            state (dict): New 'documents' key added to state, that contains the retrieved documents
    """
    
    question = state['question']
    
    documents = compression_retriever.invoke(question)
    
    return {
        'question': question,
        'documents': documents
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
    documents = state['documents']
    
    filtered_docs = []
    web_search = 'No'
    
    for doc in documents:
        score = retrieval_grader.invoke(
            {
                'question': question,
                'context': doc
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


def generate(state: AgentState) -> AgentState:
    """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
    """
    
    question = state['question']
    