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
    
    class Config:
        arbitrary_types_allowed = True 
    
    def __init__(self, host, port, user, password, table, **kwargs):
        super().__init__(
            stores_text=True, 
            is_embedding_query=True,
            **kwargs
        )
        
        self._client = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')
        self._table = table  
        self._table_schema = None  
        
        try:
            self._client.execute("SET allow_experimental_vector_similarity_index = 1")
            self._client.execute("SET allow_experimental_analyzer = 1")
        except Exception as e:
            logger.warning(f"Could not enable experimental features: {e}")

    @property
    def table(self) -> str:
        return self._table

    @property
    def client(self) -> Client:
        return self._client

    def _get_table_schema(self):
        """Get and cache table schema"""
        if self._table_schema is None:
            try:
                columns = self.client.execute(f"DESCRIBE TABLE {self.table}")
                self._table_schema = {col[0]: col[1] for col in columns}
            except Exception as e:
                logger.error(f"Error getting table schema: {e}")
                self._table_schema = {}
        return self._table_schema

    def add(self, nodes: List[BaseNode]) -> List[str]:
        logger.warning("add() method called but you're populating the table directly. Skipping.")
        return []

    def query(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """Universal query that works with any table"""
        if query.query_embedding is None:
            logger.error("Query embedding is None")
            return VectorStoreQueryResult(ids=[], similarities=[], nodes=[])
            
        vector = query.query_embedding
        top_k = query.similarity_top_k or 25
        
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
        SELECT *, cosineDistance(embedding, %(query_vector)s) AS dist
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
        
        schema = self._get_table_schema()
        column_names = list(schema.keys())
        
        ids = []
        similarities = []
        nodes = []
        
        for row in results:
            metadata = {}
            log_id = None
            text_content = None
            
            for i, col_name in enumerate(column_names):
                if i < len(row) - 1: 
                    value = row[i]
                    
                    if col_name in ['log_id', 'volume_log_id', 'event_id', 'embedding_id']:
                        log_id = str(value)
                        metadata[col_name] = value
                    elif col_name == 'text_content':
                        text_content = str(value)
                    elif col_name not in ['embedding']:
                        metadata[col_name] = value
            
            distance = row[-1]
            similarity = 1.0 - distance
            
            if log_id is None:
                log_id = str(row[0])
            
            if text_content is None:
                text_content = metadata.get('text_content', f"Record {log_id}")
            
            ids.append(log_id)
            similarities.append(similarity)
            
            node = TextNode(
                text=text_content,
                id_=log_id,
                metadata=metadata
            )
            nodes.append(node)
        
        return VectorStoreQueryResult(
            ids=ids,
            similarities=similarities,
            nodes=nodes
        )

    def get(self, text_id: str) -> List[float]:
        sql = f"SELECT embedding FROM {self.table} WHERE log_id = %(text_id)s"
        try:
            result = self.client.execute(sql, {'text_id': text_id})
            return result[0][0] if result else []
        except Exception as e:
            logger.error(f"Error getting embedding for {text_id}: {e}")
            return []

    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        sql = f"ALTER TABLE {self.table} DELETE WHERE log_id = %(ref_doc_id)s"
        try:
            self.client.execute(sql, {'ref_doc_id': ref_doc_id})
            logger.info(f"Deleted node with id {ref_doc_id}")
        except Exception as e:
            logger.error(f"Error deleting node {ref_doc_id}: {e}")
            raise

    def persist(self, persist_path: str, fs=None) -> None:
        pass