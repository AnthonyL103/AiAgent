from sentence_transformers import SentenceTransformer
from llama_index.core import Document
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

import faiss
from tqdm import tqdm
import pandas as pd
import json
import numpy as np
from clickhouse_driver import Client

client = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')
print("loading FAISS index and log texts...")
#index = faiss.read_index('log_index.faiss')
print("Loaded")


column_names = [
    'timestamp_full', 'timestamp_simple', 'TraceId', 'SpanId', 'TraceFlags',
    'SeverityText', 'SeverityNumber', 'ServiceName', 'Message', 'ResourceSchemaUrl',
    'ResourceAttributes', 'ScopeSchemaUrl', 'ScopeName', 'ScopeVersion',
    'ScopeAttributes', 'LogAttributes'
]
df = client.query_dataframe(
    "SELECT log_id, timestamp_full, ServiceName, SeverityText, Message FROM logs"
)

model = SentenceTransformer("all-MiniLM-L6-v2")
texts = (df.SeverityText + " " + df.ServiceName + " " + df.Message).tolist()
embeddings = model.encode(texts)

rows = []
#iloc gives entire row and index i 
for i in range(len(df)):
    text_content = texts[i]
    rows.append((
        df.log_id.iloc[i],
        df.timestamp_full.iloc[i], 
        df.ServiceName.iloc[i],
        df.SeverityText.iloc[i],
        df.Message.iloc[i],
        text_content,
        embeddings[i].tolist()
    ))
        

client.execute(
    """
    INSERT INTO my_vector_table (log_id, timestamp, ServiceName, SeverityText, Message, text_content, embedding)
    VALUES
    """,
    rows
)




