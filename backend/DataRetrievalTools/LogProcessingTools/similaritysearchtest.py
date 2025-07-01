from clickhouse_driver import Client
from sentence_transformers import SentenceTransformer
import re
import logging

logger = logging.getLogger(__name__)

model = SentenceTransformer("all-MiniLM-L6-v2")

client = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')

def get_db_schema():
    db_schema = []
    try:
        tables = client.execute(f"SHOW TABLES")
        db_schema = tables
    except Exception as e:
        logger.error(f"Error getting DB schema: {e}")
        db_schema = []
    
    tables = []
    for table in db_schema:
        
        cleaned = str(table)
            
        if cleaned.startswith("('"):
            cleaned = re.sub(r"\('\s*", "", cleaned)

        if cleaned.endswith("',)"):
            cleaned = re.sub(r"',\)", "", cleaned)
            
        if cleaned.endswith("auto_embeddings") or cleaned.endswith("logs"):
            continue
        
        tables.append(cleaned)
    
    return tables
        
def get_table_schema(table_name):
    table_schema = None
    try:
        columns = client.execute(f"DESC TABLE {table_name}")
        table_schema = {col[0]: col[1] for col in columns}
    except Exception as e:
        logger.error(f"Error getting table schema: {e}")
        table_schema = {}
        
    return table_schema

def perform_sim_search(prompt, table, top_k):
    
    query_vector = model.encode([prompt])[0]
    
    params = {'query_vector': list(map(float, query_vector))}
    
    sql = f"""
        SELECT *, cosineDistance(embedding, %(query_vector)s) AS dist 
        FROM {table}
        ORDER BY dist ASC 
        LIMIT {top_k}
    """
    
    try:
        results = client.execute(sql, params)
        schema = get_table_schema(table_name)
        column_names = list(schema.keys())
        metadata = {}
        log_id = None
        text_content = None
        print("result len", len(results))
        for row in results:
            text_content = None
            for i, col_name in enumerate(column_names):
                if i < len(row) -1:
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
                        
            info = ({
                "text": text_content,
                "id": log_id,
                "metadata": metadata,
                "similarity":similarity
            })
            
            print(info, "\n")
            
                    
                    
                
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return []
        

if __name__ == '__main__':
    while True:
        table_names = get_db_schema()
        
        for i in range(len(table_names)):
            print(i+1, table_names[i])
            
        table_choice = input("Given these tables enter the number of table name that you want to perform search on, else enter quit:")
        
        if table_choice.lower() == "quit":
            break
        
        table_name = table_names[int(table_choice)-1]
        
        
        top_k = input("Please enter the top k results you want to see, else enter:")
        prompt = input("Enter prompt to do similarity search test, else enter:")
        
        perform_sim_search(prompt, table_name, top_k)
        
     
        
    
    

    
    