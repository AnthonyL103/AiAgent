import numpy as np
from openai import OpenAI
import pandas as pd  
import os
import json
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.settings import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.vector_stores.types import MetadataFilters, MetadataFilter, FilterCondition
from llama_index.llms.openai import OpenAI
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import SubQuestionQueryEngine
from llama_index.core.retrievers import VectorIndexAutoRetriever
from llama_index.core.vector_stores.types import MetadataInfo, VectorStoreInfo
from DataRetrievalTools.CHVectorStore import ClickHouseVectorStore
from concurrent.futures import ThreadPoolExecutor
import asyncio

load_dotenv()

Settings.llm = OpenAI(model="gpt-4o", api_key=os.getenv("API_KEY"))
Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

def extract_columns_info(nodes):
    """Extract column names and sample values from search results"""
    columns = {}
    
    for node in nodes:
        if hasattr(node, 'metadata') and node.metadata:
            for key, value in node.metadata.items():
                if key not in columns:
                    columns[key] = set()
                if value is not None:
                    columns[key].add(str(value))
    
    return {
        column: list(values)[:5]  
        for column, values in columns.items()
    }

def sync_search_logs(prompt: str, context: str) -> dict:
    
    if not context:
        return {"error": "function needs a table name as context"}
    
    
    try:
        vector_store = ClickHouseVectorStore(
            host='localhost',
            port=9000,
            user='AgentDemo',
            password='my_database',
            table=context
        )
        
        index = VectorStoreIndex.from_vector_store(vector_store)
        
        query_engine = index.as_query_engine(
            similarity_top_k=10,
            response_mode="compact"
        )
        
        query_engine_tools = [
        QueryEngineTool(
            query_engine=query_engine,
            metadata=ToolMetadata(
                name="log_search",
                description="Useful for searching logs for specific messages, services, or timestamps",
            ),
        ),
    ]

        
        full_query_engine = SubQuestionQueryEngine.from_defaults(
        query_engine_tools=query_engine_tools,
        use_async=True,
    )
        
        query_result = full_query_engine.query(prompt)
        
        sample_logs = []
        if hasattr(query_result, 'source_nodes') and query_result.source_nodes:
            sample_logs = [node.text for node in query_result.source_nodes if hasattr(node, 'text')]
        
        columns_info = extract_columns_info(
            query_result.source_nodes if hasattr(query_result, 'source_nodes') else []
        )
        
        result = {
            "table_used": context,
            "response": str(query_result.response) if hasattr(query_result, 'response') else "",
            "sample_logs": sample_logs,
            "columns_info": columns_info,
            "total_found": len(query_result.source_nodes) if hasattr(query_result, 'source_nodes') else 0
        }
        
        return result
        
    except Exception as e:
        error_result = {
            "table_used": context,
            "error": str(e),
            "sample_logs": [],
            "columns_info": {},
            "total_found": 0
        }
        return error_result

async def search_logs_llama(prompt: str, context: str) -> dict:
    """Async wrapper that runs the sync search in a thread pool"""
    
    if not context:
        return {"error": "function needs a table name as context"}
    
    
    try:
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(
                executor,
                sync_search_logs,
                prompt,
                context
            )
        
        
        if isinstance(result, str):
            result = json.loads(result)
        
        return result
        
    except Exception as e:
        error_result = {
            "table_used": context,
            "error": f"Async execution error: {str(e)}",
            "sample_logs": [],
            "columns_info": {},
            "total_found": 0
        }
        return error_result

