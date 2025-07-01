from sentence_transformers import SentenceTransformer
from clickhouse_driver import Client
import re

client = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')

model = SentenceTransformer("all-MiniLM-L6-v2")
    
    

def get_available_columns(table_name):
    try:
        columns_df = client.query_dataframe(f"DESCRIBE TABLE {table_name}")
        all_columns = columns_df['name'].tolist()  
        
        exclude_columns = ['log_id', 'timestamp', 'text_content', 'embedding', 'embedding_id']
        
        embed_columns = [col for col in all_columns if col not in exclude_columns]
        return embed_columns
        
    except Exception as e:
        return [], []

def generate_text_content(row_data, embed_columns, embedding_table_name, log_id):
    text_parts = []
    update_parts = []
    
    for col in embed_columns:
        if col in row_data and row_data[col] is not None:
            value = str(row_data[col]).strip()
            if value and value != 'None' and value != '' and value != 'NULL':
                text_parts.append(value)
                
                if col in ['size']:  
                    update_parts.append(f"{col} = {value}")
                else:  
                    escaped_value = value.replace("'", "''")  
                    update_parts.append(f"{col} = '{escaped_value}'")
    
    if update_parts:
        source_query = f"""
        ALTER TABLE {embedding_table_name}
        UPDATE {', '.join(update_parts)}
        WHERE log_id = '{log_id}'
        """
        print(f"Executing query: {source_query}")  
        client.execute(source_query)
    
    return ' '.join(text_parts) if text_parts else 'empty_content'

def get_source_table_name(embedding_table_name):
    source_name = re.sub(r'_embeddings?$', '', embedding_table_name)

    return source_name

def process_embedding_table(embedding_table_name):
    
    try:
        source_table = get_source_table_name(embedding_table_name)
        
        id_column = 'log_id'
        
        embed_columns = get_available_columns(embedding_table_name)
        
        if not embed_columns:
            return 0
        
        empty_embeddings_query = f"""
            SELECT {id_column}
            FROM {embedding_table_name}
            WHERE length(embedding) = 0
            ORDER BY timestamp DESC
            LIMIT 50
        """
        
        empty_df = client.query_dataframe(empty_embeddings_query)
        
        if len(empty_df) == 0:
            return 0
        
        log_ids = empty_df[id_column].tolist()
        
        processed_count = 0
        
        
        for log_id in log_ids:
            try:
                
                source_id_column = 'log_id' if 'log_id' in get_available_columns(source_table)[1] else 'id'
                
                source_query = f"""
                    SELECT *
                    FROM {source_table}
                    WHERE {source_id_column} = '{log_id}'
                    LIMIT 1
                """
                
                source_df = client.query_dataframe(source_query)
                
                if len(source_df) == 0:
                    continue
                                
                row_data = source_df.iloc[0].to_dict()
                
                text_content = generate_text_content(row_data, embed_columns, embedding_table_name, log_id)
                
                embedding = model.encode([text_content])[0]  
                
                update_query = f"""
                    ALTER TABLE {embedding_table_name}
                    UPDATE 
                        text_content = %(text)s,
                        embedding = %(emb)s
                    WHERE {id_column} = %(id)s
                """
                
                client.execute(update_query, {
                    'text': text_content,
                    'emb': embedding.tolist(),
                    'id': log_id
                })
                
                processed_count += 1
                
                print(processed_count)
                
                
            except Exception as e:
                print(f"Error {e}")
                continue
        
        return processed_count
        
    except Exception as e:
        return 0

def embedding_service():
    
    try:
        tables_df = client.query_dataframe("SHOW TABLES")
        
        embedding_tables = []
        for _, row in tables_df.iterrows():
            table_name = row['name']  
            if table_name.endswith('_embeddings'):
                embedding_tables.append(table_name)
        
        
        if not embedding_tables:
            return
        
        total_processed = 0
        for table in embedding_tables:
            processed = process_embedding_table(table)
            total_processed += processed
            print(total_processed)
        
        
    except Exception as e:
        print(f"Error in main function")


if __name__ == '__main__':
    embedding_service()
            
        
