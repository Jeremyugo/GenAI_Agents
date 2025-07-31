import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.graph import interact_with_agent

import asyncio
import nest_asyncio
import random
import streamlit as st
nest_asyncio.apply()


def generate_thread_id():
    return random.randint(1, 10**10)


st.set_page_config(
    page_title="Agentic RAG 🤖",
    layout="wide",
)

async def get_response(query: str, thread_id: str):
    
    return await interact_with_agent(
        query=query,
        thread_id=thread_id
    )


def run_app() -> None:
    st.title('Agentic RAG 🤖')

    with st.sidebar:
        st.text_input(label='Enter your OpenAI API Key', key='openAI_api_key', type='password')

    if st.session_state.get('openAI_api_key'):
        if st.button("New Chat"):
            _keys = ['messages', 'thread_id']
            for key in _keys:
                st.session_state.pop(key, None)
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
                # try:
                    # Use the existing event loop instead of creating a new one
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        response = asyncio.run_coroutine_threadsafe(
                            interact_with_agent(
                                query=user_query,
                                thread_id=st.session_state['thread_id'],
                                history=st.session_state['messages']
                            ), loop
                        ).result()
                    else:
                        response = loop.run_until_complete(
                            interact_with_agent(
                                query=user_query,
                                thread_id=st.session_state['thread_id'],
                                history=st.session_state['messages']
                            )
                        )

                    with st.chat_message('assistant'):
                        st.markdown(response)
                    st.session_state['messages'].append(
                        {
                            'role': 'assistant',
                            'content': response
                        }
                    )

                # except Exception as e:
                #     st.error(str(e))
        
    return


if __name__ == '__main__':
    run_app()