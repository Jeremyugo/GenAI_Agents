import sys
import os
import asyncio

sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from loguru import logger as log
from tqdm import tqdm

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

from src.vector import prepare_data
from utils.config import ENV_FILE_PATH

load_dotenv(ENV_FILE_PATH)

neo4j_uri = os.environ.get('NEO4J_URI')
neo4j_user = os.environ.get('NEO4J_USER')
neo4j_password = os.environ.get('NEO4J_PASSWORD')

graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password)


async def create_knowledge_graph(pdf_files: list[str]) -> None:
    doc_splits = prepare_data(pdf_files)
    
    await graphiti.build_indices_and_constraints()
    
    log.info('Adding episodes to the knowledge graph...')
    for i, episode in tqdm(enumerate(doc_splits), total=len(doc_splits), desc='Adding episodes'):
        try:
            await graphiti.add_episode(
                name=f'Apple Intelligence {i}',
                episode_body=episode.page_content,
                source=EpisodeType.text,
                source_description='Bloomberg Technology',
                reference_time=datetime.now(timezone.utc),
            )
            log.info(f"Processed item {i + 1}/10")
        
        except Exception as e:
            log.error(f"Error processing item {i + 1}/10: {e}")
    
    log.success('Knowledge graph created successfully!')
    
    return 


async def search_knowledge_graph(query: str, limit: int = 5) -> str:
    node_search_config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
    node_search_config.limit = limit 

    log.info(f'Searching knowledge graph...')
    node_search_results = await graphiti._search(
        query=query,
        config=node_search_config,
    )

    knowledge_graph_info = "\n".join(
        f"Node Name: {node.name}\nContent Summary: {node.summary}\n" 
        for node in node_search_results.nodes
    )
    
    return knowledge_graph_info
