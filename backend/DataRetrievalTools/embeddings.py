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
    'id','event', 'reason', 'regarding_kind', 'regarding_name', 'regarding_namespace',
    'reporting_controller', 'type', 'cluster_id', 'event_time']

df = client.query_dataframe(
    "SELECT log_id, timestamp, name, status, type, zone, cluster_id FROM cinder_volume_logs"
)

model = SentenceTransformer("all-MiniLM-L6-v2")

texts = (
    df.name + " " + 
    df.status + " " + 
    df.type  + " " + 
    df.zone + " " + 
    df.cluster_id
).tolist()


embeddings = model.encode(texts)

rows = []
for i in range(len(df)):
    text_content = texts[i]
    rows.append((
        df.log_id.iloc[i],
        df.timestamp.iloc[i],
        df.name.iloc[i],
        df.status.iloc[i],
        df.type.iloc[i],
        df.zone.iloc[i],
        df.cluster_id.iloc[i],
        text_content,
        embeddings[i].tolist()
    ))

        

client.execute(
    """
    INSERT INTO cinder_volume_embeddings (
        volume_log_id, timestamp, name, status, type, zone, cluster_id, text_content, embedding
    )
    VALUES
    """,
    rows
)


