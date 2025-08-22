# 🤖 MultiAgent Research and Report Writing

## Overview
This project implements an advanced multi-agent system for automated research and report writing using LangChain and LangGraph. The system comprises three specialized agents working together to research topics, analyze information, and generate comprehensive reports.

## System Architecture

### Agents
1. **📝Planning Agent** (`src/agents/planner.py`)
   - Generates a structured plan to research and write the research report

2. **🧑‍💻Research Agent** (`src/agents/researcher.py`)
   - Creates section-based report outlines
   - Generates and performs multiple web searchers using Brave Search API
   - Retrieves and processes web content
   - Deduplicates and cleans search results

3. **📃Writing Agent** (`src/agents/writer.py`)
   - Generates structured writing plans
   - Integrates research findings into coherent sections
   - Produces well-organized report drafts

## Deep Research Multi-Agent Graph
![multi_agent_graph](./static/graph.png)

## Key Features
- Asynchronous web research
- Structured report generation
- Modular agent architecture
- Configurable search parameters
- Clean text processing
- Source integration in reports

## Dependencies
- LangChain
- LangGraph
- OpenAI GPT-4
- Brave Search API
- Pydantic
- aiohttp (for async operations)

## Project Structure
```
deep_researcher_multi-agent/
├── src/
│   ├── agents/
│   │   ├── planner.py      # Planning agent implementation
│   │   ├── researcher.py   # Research agent implementation
│   │   └── writer.py       # Writing agent implementation
│   ├── teams/
│   │   └── planning_team.py # Team orchestration
│   ├── prompts.py          # System prompts
│   ├── state.py           # State management
│   ├── utils.py           # Utility functions
│   └── helper.py          # Helper functions
```

## Usage
The system can be used to:
- Generate research plans for any given topic
- Perform automated web research
- Create structured reports with proper source integration
- Handle complex research tasks with multiple subtopics

## Technical Implementation
- Built on LangGraph for agent orchestration
- Uses LangChain for LLM interactions
- Implements async operations for efficient web searches
- Employs structured data validation with Pydantic
- Features modular and extensible architecture
