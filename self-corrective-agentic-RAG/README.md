# Agentic Self-Corrective RAG with Hybrid Vector Store & Knowledge Graph 🤖

This project is an advanced information retrieval and generation system (RAG) designed to produce more accurate, 
reliable answers by combining semantic information from a vector store, relationships from a knowledge graph and self
correcting logic. 
Traditional RAG (Retrieval-Augmented Generation) systems rely mainly on a vector store, which retrieves content based on 
semantic similarity to a user's query. However, vector stores alone often miss relationships between data. 

**This project improves on that by adding:**
- Agents that guide the system, evaluate results, and decide next steps. 
- A knowledge graph, which understands the relationship between data points. 
- A feedback loop, where the system checks and corrects its own results. 
- A web search tool, which searches for additional information if required. 

This creates a smarter system that retrieves better information and generates more accurate responses. 

**Key Features:**
- Classifies User query into either 'Conversational' (Trigger Chat Bot) or 'Informational' (Trigger RAG Agent)
- Combines semantic search (vector store) with structured relationship-based search (knowledge graph). 
- Uses an LLM (language model) to filter and correct results before generating an answer. 
- Automatically performs a web search if local data isn't enough. 
- All steps are orchestrated by agents that guide decisions and improve accuracy. 

**Tech Stack:**
- Python 
- LangGraph, LangChain (agent and flow management) 
- Qdrant + Neo4j + Graphiti (vector search + knowledge graph) 
- FlashRank (smart document re-ranking) 
- Streamlit (interactive front-end) 


### Knowledge Graph 🎯
<p>
  <img src="./static/graphiti_KG.png" width="500" height="400" />
</p>

### Graph Flow
**Current Version:** Added

<img src="./static/graph_flow_v1.png" width="400" style="margin-right:10px;" />

**Previous Version**

<img src="./static/graph_flow_v0.png" width="400" style="margin-right:10px;" />