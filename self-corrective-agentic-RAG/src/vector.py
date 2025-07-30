import os
import sys
import tempfile
from pathlib import Path
from xmlrpc import client

from dotenv import load_dotenv
from loguru import logger as log

from langchain.retrievers import ContextualCompressionRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_compressors import FlashrankRerank
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Qdrant
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.config import ENV_FILE_PATH
from utils.helper_functions import create_qdrant_client

load_dotenv(ENV_FILE_PATH)


qdrant_client = create_qdrant_client(
    url=os.getenv('QDRANT_URL'),
    api_key=os.getenv('QDRANT_API_KEY'),
    collection_name='self_corrective_agentic_rag'
)


llm = ChatOpenAI(model='gpt-3.5-turbo')



def prepare_data(pdf_files: list[str]) -> list:
    docs = []

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
    split_docs = splitter.split_documents(docs)
    
    return [doc for doc in split_docs if doc.page_content]


def create_vector_database(pdf_files: list[str], collection_name: str = 'self_corrective_agentic_rag') -> None:
    doc_splits = prepare_data(pdf_files)
    
    if collection_name not in [c.name for c in client.get_collections().collections]:
        log.info(f'Creating new collection: {collection_name}')
        
        Qdrant.from_documents(
            api_key=os.getenv('QDRANT_API_KEY'),
            url=os.getenv('QDRANT_URL'),
            documents=doc_splits,
            embedding=OpenAIEmbeddings,
            collection_name=collection_name,
        )
    
    log.success('Vector store created successfully!')
    
    return


def add_reranker(vectorstore: Qdrant) -> ContextualCompressionRetriever:
    
    retriever = vectorstore.as_retriever(search_kwargs={'k': 7})
    
    compressor = FlashrankRerank(top_n=3)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=retriever
    )
    
    return compression_retriever


def add_documents_to_vectorstore(pdf_paths: list[str], collection_name: str = 'self_corrective_agentic_rag') -> None:
    
    doc_splits = prepare_data(pdf_paths)
    
    vectorstore = Qdrant(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=OpenAIEmbeddings()
    )
    vectorstore.add_documents(doc_splits)

    log.success('New PDF documents added to vectorstore!')
    
    return


def create_vector_retriever(collection_name: str = 'self_corrective_agentic_rag') -> ContextualCompressionRetriever:
    vectorstore = Qdrant(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=OpenAIEmbeddings()
    )
    
    retriever = vectorstore.as_retriever(
        search_type='mmr',
        search_kwargs={'k':7}
    )
    
    compressor = FlashrankRerank(top_n=3)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=retriever
    )
    
    return compression_retriever



if __name__ == '__main__':
    pdf_paths = ['/home/ubuntu/datascience/Generative-AI-Agents-langChain-langGraph-/self-corrective-agentic-RAG/data/data.pdf']
    create_vector_database(pdf_paths)
