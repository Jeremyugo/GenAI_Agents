from langchain_core.prompts import ChatPromptTemplate
from langchain import hub


# Answer Generation prompt 
generate_system_prompt = """
You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.
Conversation history: {history}
Question: {question} 
Context: {context} 
Answer:
"""
generate_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", generate_system_prompt),
        ("human", "Conversation history: {history} \n\n Question: {question} \n\n Context: {context}"),
    ]
)



# Document/Context grading prompt
grade_system_prompt = """You are a grader assessing relevance of a retrieved document to a user question. \n 
    If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", grade_system_prompt),
        ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
    ]
)


# Query/Question rewrite prompt
re_write_system_prompt = """You a question re-writer that converts an input question to a better version that is optimized \n 
     for web search. Look at the input and try to reason about the underlying semantic intent / meaning."""
re_write_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", re_write_system_prompt),
        (
            "human",
            "Here is the initial question: \n\n {question} \n Formulate an improved question.",
        ),
    ]
)


query_classifer_system_prompt = """
    You are a query classifier in a retrieval-augmented system.

    Classify the user's query into one of the following types:

    1. "conversational" - casual talk, greetings, jokes, opinions, chit-chat.
    2. "informational" - questions that require facts, knowledge, or external data to answer.

    Only return one word: either "conversational" or "informational".

    Query: "{query}"
    Classification:
"""
query_classifier_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", query_classifer_system_prompt),
        ("human", "{query}"),
    ]
)