import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.graph import interact_with_agent

import random
import streamlit as st


def generate_thread_id():
    return random.randint(1, 10**10)


st.set_page_config(
    page_title="SQL Agent 🤖",
    layout="wide",
)


def run_app() -> None:
    st.title('SQL Agent 🤖')
        
    with st.sidebar:
        st.text_input(label='Enter your OpenAI API Key', key='openAI_api_key', type='password')
    
    if st.session_state.get('openAI_api_key'):
        if st.button("New Chat"):
            st.session_state.pop('messages', None)
            st.session_state.pop('thread_id', None)
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
                        session_id=st.session_state['thread_id']
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