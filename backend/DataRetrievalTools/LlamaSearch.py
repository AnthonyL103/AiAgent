
import numpy as np
from openai import OpenAI
import pandas as pd  
import os
import json
from dotenv import load_dotenv
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.settings import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.vector_stores.types import MetadataFilters, MetadataFilter, FilterCondition
from llama_index.llms.openai import OpenAI
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import SubQuestionQueryEngine
from llama_index.core.retrievers import VectorIndexAutoRetriever
from llama_index.core.vector_stores.types import MetadataInfo, VectorStoreInfo


load_dotenv()


Settings.llm = OpenAI(model="gpt-4o", api_key=os.getenv("API_KEY"))

Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

storage_context = StorageContext.from_defaults(persist_dir="DataRetrievalTools/LlamaIndex/index_storage")
index = load_index_from_storage(storage_context)

vector_store_info = VectorStoreInfo(
    content_info="System logs containing embedded information about severity levels (WARN, INFO), service names (Accounting, Ad), process runtimes (OpenJDK Runtime Environment, .NET), and detailed log messages. Content includes semantic information about high CPU load, ad requests, order details, etc.",
    metadata_info=[
        MetadataInfo(
            name="timestamp",
            type="str",
            description="Timestamp in format 'YYYY-MM-DD HH:MM:SS.nnnnnnnnn' (with nanoseconds). Example: '2025-06-08 11:31:41.222813500'. All logs are from June 8th, 2025. Use this for time-based filtering."
        ),
        
    ],
)

retriever = VectorIndexAutoRetriever(
    index,
    retriever_mode="hybrid",
    vector_store_info=vector_store_info,
    similarity_top_k=25,
    verbose=True 
    
)
query_engine = RetrieverQueryEngine(retriever=retriever)


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
        if node.metadata:
            for key, value in node.metadata.items():
                if key not in columns:
                    columns[key] = set()
                columns[key].add(str(value))
    
    return {
        column: list(values)[:5]  
        for column, values in columns.items()
    }

async def search_logs_llama(prompt: str) -> str:
    query_result = query_engine.query(prompt)
    
    sample_logs = [node.text for node in query_result.source_nodes]
    
    columns_info = extract_columns_info(query_result.source_nodes)
    
    
    
    result = {
        "sample_logs": sample_logs,
        "columns_info": columns_info,
        "total_found": len(query_result.source_nodes)
    }
    print(result)
    
    return json.dumps(result, indent=2)

