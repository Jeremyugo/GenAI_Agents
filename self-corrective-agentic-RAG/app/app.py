import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.graph import interact_with_agent
from src.vector import create_vector_database

import random
import uuid
import streamlit as st


def generate_thread_id():
    return random.randint(1, 10**10)


st.set_page_config(
    page_title="Agentic RAG 🤖",
    layout="wide",
)


def run_app() -> None:
    st.title('Agentic RAG 🤖')

    with st.sidebar:
        st.text_input(label='Enter your OpenAI API Key', key='openAI_api_key', type='password')
        st.session_state.setdefault('uploader_key', 'defualt_uploader')
        if st.session_state.get('openAI_api_key'):
            uploaded_files = st.file_uploader(
                'Choose PDF files to upload',
                type='pdf',
                accept_multiple_files=True,
                help='Upload PDF files to create a vector store for the agent.',
                key=st.session_state['uploader_key']
            )
            st.session_state.setdefault('vector_store_created', False)

            if uploaded_files and not st.session_state.get('vector_store_created'):
                st.success('PDF files uploaded successfully!')
                create_vector_database(uploaded_files)
                st.session_state['vector_store_created'] = True

    
    if st.session_state.get('openAI_api_key') and st.session_state.get('uploader_key'):
        if st.button("New Chat"):
            _keys = ['messages', 'thread_id', 'uploader_key', 'vector_store_created']
            for key in _keys:
                st.session_state.pop(key, None)
            st.session_state['uploader_key'] = str(uuid.uuid4())
            st.rerun()
        
        st.session_state.setdefault('thread_id', generate_thread_id())
        st.session_state.setdefault('messages', [])
        
        for message in st.session_state['messages']:
            with st.chat_message(message['role']):
                st.markdown(message['content'])
                
        if user_query := st.chat_input("Ask a question:"):
            with st.chat_message("user"):
                st.markdown(user_query)
            st.session_state.messages.append({"role": "user", "content": user_query})
            
            with st.spinner('Thinking...'):
                try:
                    response = interact_with_agent(
                        query=user_query,
                        thread_id=st.session_state['thread_id']
                    )
                    
                    with st.chat_message('assistant'):
                        st.markdown(response)
                    st.session_state['messages'].append(
                        {
                            'role': 'assistant',
                            'content': response
                        }
                    )
                    
                except Exception as e:
                    st.error(str(e))
        
    
    return


if __name__ == '__main__':
    run_app()