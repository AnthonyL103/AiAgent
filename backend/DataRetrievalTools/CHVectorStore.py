from llama_index.core.vector_stores.types import BasePydanticVectorStore
from llama_index.core.vector_stores import (
    VectorStoreQuery,
    VectorStoreQueryResult,
)
from typing import List, Any, Optional
from llama_index.core.schema import BaseNode, TextNode
from clickhouse_driver import Client
from pydantic import Field
import logging

logger = logging.getLogger(__name__)

class ClickHouseVectorStore(BasePydanticVectorStore):
    stores_text: bool = Field(default=True)
    is_embedding_query: bool = Field(default=True)
     # Initialize Pydantic fields, pydantic is for data validation and serialization, its a smart way to define classes that auto validate 
    # data types and convert data types like 123 string into 123 integer, provide clear error msg, serilaize/deserialize lik convert from JSON to dict
    # super goes up inheritance chain to llama index parent class for initializing custom vectore store wrappers
    class Config:
        arbitrary_types_allowed = True 
    
    def __init__(self, host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760', table='my_vector_table', **kwargs):
        super().__init__(
            stores_text=True, 
            is_embedding_query=True,
            **kwargs
        )
        
        self._client = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')
        self._table = table  
        
        try:
            self._client.execute("SET allow_experimental_vector_similarity_index = 1")
            self._client.execute("SET allow_experimental_analyzer = 1")
        except Exception as e:
            logger.warning(f"Could not enable experimental features: {e}")

    @property
    def table(self) -> str:
        """Get the table name."""
        return self._table

    @property
    def client(self) -> Client:
        """Return the ClickHouse client instance."""
        return self._client

    def add(self, nodes: List[BaseNode]) -> List[str]:
        """Add nodes to index. Not used in your workflow since you populate directly."""
        logger.warning("add() method called but you're populating the table directly. Skipping.")
        return []

    def query(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """Query the vector store."""
        if query.query_embedding is None:
            logger.error("Query embedding is None")
            return VectorStoreQueryResult(ids=[], similarities=[], nodes=[])
            
        vector = query.query_embedding
        top_k = query.similarity_top_k or 25
        
        # Build WHERE clause for metadata filters
        where_clause = ""
        params = {'query_vector': vector}
        
        if query.filters:
            conditions = []
            for i, filter_item in enumerate(query.filters.filters):
                param_name = f'filter_{i}'
                if filter_item.operator == "==":
                    conditions.append(f"{filter_item.key} = %({param_name})s")
                elif filter_item.operator == "!=":
                    conditions.append(f"{filter_item.key} != %({param_name})s")
                elif filter_item.operator == ">":
                    conditions.append(f"{filter_item.key} > %({param_name})s")
                elif filter_item.operator == "<":
                    conditions.append(f"{filter_item.key} < %({param_name})s")
                params[param_name] = filter_item.value
            
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
        
        sql = f"""
        SELECT log_id, text_content, timestamp, Message, ServiceName, SeverityText, process_runtime,
               cosineDistance(embedding, %(query_vector)s) AS dist
        FROM {self.table}
        {where_clause}
        ORDER BY dist ASC
        LIMIT {top_k}
        """
        
        try:
            results = self.client.execute(sql, params)
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return VectorStoreQueryResult(ids=[], similarities=[], nodes=[])
        
        ids = []
        similarities = []
        nodes = []
        
        for r in results:
            log_id, text_content, timestamp, Message, service_name, severity_text, process_runtime, distance = r
            
            # Convert cosine distance to similarity (1 - distance)
            similarity = 1.0 - distance
            
            ids.append(str(log_id))  # Convert UUID to string
            similarities.append(similarity)
            
            # Create TextNode with metadata
            metadata = {
                'timestamp': timestamp,
                'Message': Message,
                'ServiceName': service_name,
                'SeverityText': severity_text,
                'process_runtime': process_runtime
            }
            
            node = TextNode(
                text=text_content,
                id_=str(log_id),  
                metadata=metadata
            )
            nodes.append(node)
        
        return VectorStoreQueryResult(
            ids=ids,
            similarities=similarities,
            nodes=nodes
        )

    def get(self, text_id: str) -> List[float]:
        """Get embedding by text_id."""
        sql = f"SELECT embedding FROM {self.table} WHERE log_id = %(text_id)s"
        try:
            result = self.client.execute(sql, {'text_id': text_id})
            return result[0][0] if result else []
        except Exception as e:
            logger.error(f"Error getting embedding for {text_id}: {e}")
            return []

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """Delete by ref_doc_id."""
        sql = f"ALTER TABLE {self.table} DELETE WHERE log_id = %(ref_doc_id)s"
        try:
            self.client.execute(sql, {'ref_doc_id': ref_doc_id})
            logger.info(f"Deleted node with id {ref_doc_id}")
        except Exception as e:
            logger.error(f"Error deleting node {ref_doc_id}: {e}")
            raise

    def persist(self, persist_path: str, fs=None) -> None:
        """Persist is handled by ClickHouse itself."""
        pass
       