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

vector_store = ClickHouseVectorStore(
    host='localhost',
    port=9000,
    user='AgentDemo',
    password='my_database',
    table='my_vector_table'
)

load_dotenv()

Settings.llm = OpenAI(model="gpt-4o", api_key=os.getenv("API_KEY"))
Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

index = VectorStoreIndex.from_vector_store(vector_store)

vector_store_info = VectorStoreInfo(
    content_info="Embedded plaintext parts of System logs",
    metadata_info=[
        MetadataInfo(
            name="timestamp",
            type="str",
            description="Log timestamps are in format 'YYYY-MM-DD HH:MM:SS'"
        ),
    ],
)

retriever = VectorIndexAutoRetriever(
    index,
    vector_store_info=vector_store_info,
    similarity_top_k=25,
    verbose=True 
)

query_engine = RetrieverQueryEngine.from_args(
    retriever=retriever,
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

async def search_logs_llama(prompt: str) -> dict:
    """Search logs using LlamaIndex with improved error handling"""
    try:
        query_result = query_engine.query(prompt)
        
        sample_logs = []
        if hasattr(query_result, 'source_nodes') and query_result.source_nodes:
            sample_logs = [node.text for node in query_result.source_nodes if hasattr(node, 'text')]
        
        columns_info = extract_columns_info(
            query_result.source_nodes if hasattr(query_result, 'source_nodes') else []
        )
        
        result = {
            "response": str(query_result.response) if hasattr(query_result, 'response') else "",
            "sample_logs": sample_logs,
            "columns_info": columns_info,
            "total_found": len(query_result.source_nodes) if hasattr(query_result, 'source_nodes') else 0
        }
        
        print(result)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "error": str(e),
            "sample_logs": [],
            "columns_info": {},
            "total_found": 0
        }
        print(f"Error in search_logs_llama: {e}")
        return json.dumps(error_result, indent=2)

# Synchronous version for non-async usage
def search_logs_llama_sync(prompt: str) -> dict:
    """Synchronous version of log search"""
    try:
        query_result = query_engine.query(prompt)
        
        sample_logs = []
        if hasattr(query_result, 'source_nodes') and query_result.source_nodes:
            sample_logs = [node.text for node in query_result.source_nodes if hasattr(node, 'text')]
        
        columns_info = extract_columns_info(
            query_result.source_nodes if hasattr(query_result, 'source_nodes') else []
        )
        
        result = {
            "response": str(query_result.response) if hasattr(query_result, 'response') else "",
            "sample_logs": sample_logs,
            "columns_info": columns_info,
            "total_found": len(query_result.source_nodes) if hasattr(query_result, 'source_nodes') else 0
        }
        
        print(result)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "error": str(e),
            "sample_logs": [],
            "columns_info": {},
            "total_found": 0
        }
        print(f"Error in search_logs_llama_sync: {e}")
        return json.dumps(error_result, indent=2)
    
if __name__ == '__main__':
    prompt = "find me logs with high cpu"
    result = search_logs_llama_sync(prompt)
    print(result)
    