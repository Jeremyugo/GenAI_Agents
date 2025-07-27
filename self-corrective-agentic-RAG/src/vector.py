import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.document_compressors import FlashrankRerank
from utils.config import ENV_FILE_PATH, VECTORSTORE_PATH

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv(ENV_FILE_PATH)

from loguru import logger as log

llm = ChatOpenAI(model='gpt-3.5-turbo')


def prepare_data(urls: list[str]):
    
    docs = [WebBaseLoader(url).load() for url in urls]
    docs_list = [item for sublist in docs for item in sublist]
    
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=250,
        chunk_overlap=50
    )
    
    doc_splits = text_splitter.split_documents(docs_list)
    
    return doc_splits



def add_reranker(vectorstore):
    
    retriever = vectorstore.as_retriever(search_kwargs={'k': 7})
    
    compressor = FlashrankRerank(top_n=3)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=retriever
    )
    
    return compression_retriever



def create_vector_database(urls: list[str]):
    
    doc_splits = prepare_data(urls)
    
    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name='rag-chroma',
        embedding=OpenAIEmbeddings(),
        persist_directory=VECTORSTORE_PATH
    )
    
    log.success('Created new Chroma vectorstore')
    
    return 



def add_documents_to_vectorstore(urls: list[str]):
    
    vectorstore = Chroma(
        collection_name='rag-chroma',
        persist_directory=VECTORSTORE_PATH,
        embedding_function=OpenAIEmbeddings()
    )
    
    doc_splits = prepare_data(urls)
    
    vectorstore.add_documents(doc_splits)
    vectorstore.persist()

    log.success('New documents added to vectore!')
    
    return


def create_vectore_retriever():
    
    vectorstore = Chroma(
        collection_name='rag-chroma',
        persist_directory=VECTORSTORE_PATH,
        embedding_function=OpenAIEmbeddings()
    )
    
    
    compression_reranker = add_reranker(vectorstore)
    
    return compression_reranker