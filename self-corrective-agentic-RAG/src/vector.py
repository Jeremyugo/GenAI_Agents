import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.document_compressors import FlashrankRerank
from utils.config import ENV_FILE_PATH, VECTORSTORE_PATH
import tempfile
import shutil

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv(ENV_FILE_PATH)

from loguru import logger as log

llm = ChatOpenAI(model='gpt-3.5-turbo')


def clear_vectorstore_directory():
    import stat
    if os.path.exists(VECTORSTORE_PATH):
        try:
            shutil.rmtree(VECTORSTORE_PATH)
            log.success(f'Cleared directory')
        except Exception as e:
            log.error(f'Failed to clear vectorstore directory: {e}')
            raise
    try:
        os.makedirs(VECTORSTORE_PATH, exist_ok=True)
        os.chmod(VECTORSTORE_PATH, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    except Exception as e:
        log.error(f'Failed to create or set permissions for vectorstore directory: {e}')
        raise
    return


def prepare_data(pdf_files):
    #clear_vectorstore_directory()
    docs = []
    # for pdf in pdf_files:
    #     if hasattr(pdf, 'read'):
    #         with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
    #             tmp_file.write(pdf.read())
    #             tmp_file_path = tmp_file.name
    #         loader = PyPDFLoader(tmp_file_path)
    #         docs.extend(loader.load())
    #         os.remove(tmp_file_path)
    #     else:
    #         loader = PyPDFLoader(pdf)
    #         docs.extend(loader.load())
    for pdf in pdf_files:
        if hasattr(pdf, 'read'):
            pdf_bytes = pdf.read()
            tmp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(pdf_bytes)
                    tmp_file_path = tmp_file.name

                loader = PyPDFLoader(tmp_file_path)
                docs.extend(loader.load())

            finally:
                if tmp_file_path and os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)

        else:
            loader = PyPDFLoader(pdf)
            docs.extend(loader.load())

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=250,
        chunk_overlap=50
    )
    return splitter.split_documents(docs)


def create_vector_database(pdf_files):
    
    doc_splits = prepare_data(pdf_files)
    log.info(
        f'Data snippet: {doc_splits[-1].page_content[:50]}...'
    )
    Chroma.from_documents(
        documents=doc_splits,
        collection_name='rag-chroma',
        embedding=OpenAIEmbeddings(),
        persist_directory=VECTORSTORE_PATH
    )
    log.success('Vector store created successfully!')
    return



def add_reranker(vectorstore):
    
    retriever = vectorstore.as_retriever(search_kwargs={'k': 7})
    
    compressor = FlashrankRerank(top_n=3)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=retriever
    )
    
    return compression_retriever


def add_documents_to_vectorstore(pdf_paths: list[str]):
    """
    Adds new PDF documents to an existing Chroma vector store.
    Args:
        pdf_paths (list[str]): List of PDF file paths.
    """
    vectorstore = Chroma(
        collection_name='rag-chroma',
        persist_directory=VECTORSTORE_PATH,
        embedding_function=OpenAIEmbeddings()
    )
    doc_splits = prepare_data(pdf_paths)
    vectorstore.add_documents(doc_splits)
    vectorstore.persist()
    log.success('New PDF documents added to vectorstore!')
    return


def create_vector_retriever():
    
    vectorstore = Chroma(
        collection_name='rag-chroma',
        persist_directory=VECTORSTORE_PATH,
        embedding_function=OpenAIEmbeddings()
    )
    
    
    compression_reranker = add_reranker(vectorstore)
    
    return compression_reranker


if __name__ == '__main__':
    pdf_paths = ['/home/ubuntu/datascience/Generative-AI-Agents-langChain-langGraph-/self-corrective-agentic-RAG/static/Github Repository Plan.pdf']
    create_vector_database(pdf_paths)
    