from langchain_core.prompts import ChatPromptTemplate
from langchain import hub


# Answer Generation prompt 
generate_system_prompt = """
You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.
Question: {user_question} 
Context: {context} 
Answer:
"""
generate_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", generate_system_prompt),
        ("human", "Question: {user_question} \n\n Context: {context}"),
    ]
)


# Document/Context grading prompt
grade_system_prompt = """You are a grader assessing relevance of a retrieved document to a user question. \n 
    If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", grade_system_prompt),
        ("human", "Retrieved document: \n\n {document} \n\n User question: {user_question}"),
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
            "Here is the initial question: \n\n {user_question} \n Formulate an improved question.",
        ),
    ]
)


# Question extraction
question_extraction_system_prompt = """
You are a question extraction assistant. 
Your task is to read the user’s message and identify ONLY the core question(s) that are relevant to Bloomberg's March 14, 2025 
report on Apple's AI initiative, Apple Intelligence. This document covers delays in AI feature rollouts, Siri’s redesign, 
leadership and organizational changes, AI startup acquisitions, technical challenges (on-device vs cloud, performance issues), 
competitive positioning, financial impacts, and Apple’s recovery strategy.

Ignore greetings, context, or extra wording. Return the extracted question(s) in plain text, nothing else.

Examples:
User: "Can you tell me Apple's biggest competitors?" 
Output: "What are Apple's biggest competitors?"

User: "Hi, could you explain what problems Siri is facing with AI?" 
Output: "What problems is Siri facing with AI?"

User: "I'm curious, how much did Apple spend on acquisitions?" 
Output: "How much did Apple spend on acquisitions?"
"""
question_extraction_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", question_extraction_system_prompt),
        ("human", "{messages}"),
    ]
)


tool_description = """
Search and return information about Bloomberg's March 14, 2025 report on Apple's AI initiative, Apple Intelligence. 
The tool can return details about delayed features, Siri’s redesign, leadership changes, acquisitions, technical challenges, 
financial impact, competitive positioning, and Apple’s recovery strategy. Useful for answering questions about Apple’s AI 
struggles, market position, and long-term strategy in the AI space.
"""