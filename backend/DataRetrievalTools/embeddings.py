from sentence_transformers import SentenceTransformer
from llama_index.core import Document
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

import faiss
from tqdm import tqdm
import pandas as pd
import json
import numpy as np



print("loading FAISS index and log texts...")
#index = faiss.read_index('log_index.faiss')
print("Loaded")



column_names = [
    'timestamp_full', 'timestamp_simple', 'unknown1', 'unknown2', 'unknown3', 
    'SeverityText', 'unknown4', 'ServiceName', 'message', 'schema_url', 'metadata_json', 
    'unknown5', 'class_name', 'unknown6', 'unknown7', 'order_result_json'
]

df = pd.read_csv('testlog.csv', names=column_names)


documents = []
for row in df.itertuples(index=False):
    metadata_str = row.metadata_json.replace("'", '"')
    try:
        metadata = json.loads(metadata_str)
    except json.JSONDecodeError:
        metadata = {}
    process_runtime = metadata.get('process.runtime.name', '')
    text = f"{row.SeverityText} {row.ServiceName} {process_runtime} {row.message}"
    print(f"Processing row: ServiceName: {row.ServiceName}, SeverityText: {row.SeverityText}, Process Runtime: {process_runtime}")
    #print("Text:", text)
    #print(f"Processing row: {row.timestamp_full}, ServiceName: {row.ServiceName}, SeverityText: {row.SeverityText}, Process Runtime: {process_runtime}")
            
    doc = Document(text=text, metadata={"timestamp": str(row.timestamp_full), "ServiceName": str(row.ServiceName) or "UNAVAILABLE", "SeverityText": str(row.SeverityText) or "UNAVAILABLE", "process_runtime": str(process_runtime) or "UNAVAILABLE"})
    documents.append(doc)
        

model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")
index = VectorStoreIndex.from_documents(documents, embed_model=model)
index.storage_context.persist(persist_dir="./LlamaIndex/index_storage")




'''
def get_embeddings_batch(texts, batch_size):
    all_embeddings = []
    for i in tqdm(range(0, len(texts), batch_size)):
        
        batch = texts[i:i+batch_size]
        batch_embeddings = model.encode(batch, normalize_embeddings=True)
        all_embeddings.extend(batch_embeddings)

    return np.array(all_embeddings).astype('float32')

embeddings = get_embeddings_batch(log_texts, 50)

#gets dimension of each vector
d = embeddings.shape[1]

#creates index where flat represents exact search and L2 is the euclidean distance between the vectors
index = faiss.IndexFlatL2(d)

index.add(embeddings)
print("built the FAISS index")

#saves index to disc in log_index file
faiss.write_index(index, 'log_index')
df.to_csv('log_texts.csv', index=False)

'''