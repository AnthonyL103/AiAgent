from sentence_transformers import SentenceTransformer
from clickhouse_driver import Client
from openai import OpenAI
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')

openai_client = OpenAI(api_key=os.getenv("API_KEY"))
model = SentenceTransformer("all-MiniLM-L6-v2")


def analyze_table_for_embedding(table_name, sample_data):
    sample_data_clean = sample_data.copy()
    for col in sample_data_clean.columns:
        if sample_data_clean[col].dtype == 'object':
            sample_data_clean[col] = sample_data_clean[col].astype(str)
    
    sample_dict = sample_data_clean.head(3).to_dict('records')
    columns_info = []
    
    for col in sample_data.columns:
        col_type = str(sample_data[col].dtype)
        sample_values = sample_data[col].dropna().head(3).tolist()
        safe_sample_values = []
        for v in sample_values:
            try:
                safe_sample_values.append(str(v))
            except:
                safe_sample_values.append("complex_object")
        
        columns_info.append({
            "column_name": col,
            "data_type": col_type,
            "sample_values": safe_sample_values
        })
    
    json_safe_sample = []
    for record in sample_dict:
        safe_record = {}
        for key, value in record.items():
            try:
                json.dumps(value)
                safe_record[key] = value
            except (TypeError, ValueError):
                safe_record[key] = str(value)
        json_safe_sample.append(safe_record)
    
    prompt = f"""
    Analyze this database table for semantic embedding potential:

    Table Name: {table_name}
    
    Columns and Sample Data:
    {json.dumps(columns_info, indent=2)}
    
    Sample Records:
    {json.dumps(json_safe_sample, indent=2)}
    
    Instructions:
    1. Determine if this table contains data that would benefit from semantic search/embedding
    2. If YES, identify which columns should be embedded together to create meaningful text
    3. Consider: text fields, categorical data, meaningful IDs, status fields, names, descriptions
    4. Exclude: UUIDs, timestamps, pure numeric IDs, binary data, large numeric values
    5. The columns 'log_id', 'timestamp', 'text_content', 'embedding', 'embedding_id' are already included in any embedding table so don't include those columns. 
    
    Return ONLY a JSON object with this structure:
    {{
        "should_embed": true/false,
        "reasoning": "explanation of decision",
        "embed_columns": ["column1", "column2", "column3"],
        "text_pattern": "suggested pattern like 'status: {{status}} service: {{service_name}} message: {{message}}'",
        "table_description": "brief description of what this table contains"
    }}
    
    Examples of good embedding candidates:
    - Log tables with service names, error messages, severity levels
    - Event tables with event types, descriptions, resource names
    - User activity with actions, resources, descriptions
    
    Examples of poor embedding candidates:
    - Pure numeric/financial data without text context
    - Tables with only IDs and timestamps
    - Binary data or encoded content
    """
    
    try:
        
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content
        
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        json_str = response_text[start_idx:end_idx]
        
        analysis = json.loads(json_str)
        return analysis
        
    except Exception as e:
        print(f"Error analyzing table with OpenAI: {e}")
        

def create_embedding_table_sql(embedding_table_name, source_columns, embed_columns):
    
    base_columns = [
        "embedding_id UUID DEFAULT generateUUIDv4()",
        "log_id String",  
        "timestamp DateTime"  
    ]
    
    exclude_system_cols = ['id', 'timestamp', 'timestamp_full', 'event_time', 'created_at', 'updated_at']
    
    for col_name, col_type, *_ in source_columns:
        if col_name in embed_columns and col_name not in exclude_system_cols:
            if 'String' in col_type:
                base_columns.append(f"{col_name} String")
            elif 'LowCardinality' in col_type:
                base_columns.append(f"{col_name} {col_type}")
            elif 'Int' in col_type or 'UInt' in col_type:
                base_columns.append(f"{col_name} {col_type}")
            elif 'Float' in col_type:
                base_columns.append(f"{col_name} {col_type}")
            elif 'DateTime' in col_type:
                base_columns.append(f"{col_name} {col_type}")
            else:
                base_columns.append(f"{col_name} String") 
    
    base_columns.extend([
        "text_content String",
        "embedding Array(Float32) DEFAULT []"
    ])
    
    columns_sql = ",\n    ".join(base_columns)
    
    return f"""
        CREATE TABLE {embedding_table_name} (
            {columns_sql}
        ) ENGINE = MergeTree
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (timestamp, log_id)
        """

def create_materialized_view_sql(source_table, embedding_table, source_columns):
    
    column_names = [col[0] for col in source_columns]
    
    id_col = None
    for col_name in column_names:
        if col_name.lower() in ['id', 'log_id', 'event_id', 'record_id']:
            id_col = col_name
            break
    
    if not id_col:
        print(f"Warning: No ID column found in {source_table}. Available columns: {column_names}")
        return None
    
    select_columns = [
        "generateUUIDv4() as embedding_id",  
        f"{id_col} as log_id"                
    ]
    
    columns_sql = ",\n    ".join(select_columns)
    
    return f"""
        CREATE MATERIALIZED VIEW {source_table}_auto_embeddings 
        TO {embedding_table} AS
        SELECT 
            {columns_sql}
        FROM {source_table}
        """

def create_table(table_name):
    
    embedding_table_name = table_name + "_embeddings"
    
    try:
        table_exists = client.execute(f"EXISTS TABLE {embedding_table_name}")
        if table_exists[0][0]:
            print(f"{embedding_table_name} already exists")
            return True
        
        log_example = client.query_dataframe(f"SELECT * FROM {table_name} LIMIT 10")
        
        if len(log_example) == 0:
            print(f"No data found in {table_name}")
            return False
        
        schema_query = f"DESC TABLE {table_name}"
        schema_result = client.execute(schema_query)
        source_columns = [(row[0], row[1]) for row in schema_result]  
        
        analysis = analyze_table_for_embedding(table_name, log_example)
        
        print(f"  OpenAI Analysis Results:")
        print(f"   Should embed: {analysis['should_embed']}")
        print(f"   Reasoning: {analysis['reasoning']}")
        print(f"   Columns to embed: {analysis['embed_columns']}")
        print(f"   Description: {analysis['table_description']}")
        
        if not analysis['should_embed']:
            return False
        
        available_columns = [col[0] for col in source_columns]
        valid_embed_columns = [col for col in analysis['embed_columns'] if col in available_columns]
        
        if not valid_embed_columns:
            print(f"  None of the suggested embed columns exist in {table_name}")
            return False
        
        create_table_sql = create_embedding_table_sql(
            embedding_table_name, 
            source_columns, 
            valid_embed_columns
        )
        
        print(f"  Creating embedding table...")
        client.execute(create_table_sql)
        
        mv_sql = create_materialized_view_sql(
            table_name,
            embedding_table_name,
            source_columns,
        )
        
        if mv_sql is None:
            print(f"   Could not create materialized view - missing required columns")
            client.execute(f"DROP TABLE IF EXISTS {embedding_table_name}")
            return False
        
        client.execute(mv_sql)
        
        return True
        
    except Exception as e:
        print(f"Error processing {table_name}: {e}")
        return False

def discover_and_create_embedding_tables():
    
    tables = client.execute("SHOW TABLES")
    
    for table_row in tables:
        table_name = table_row[0]
        
        if table_name.endswith('_embeddings'):
            continue
            
        if table_name.endswith('_auto_embeddings'):
            continue
        
        if table_name.startswith('system.') or table_name.startswith('.'):
            continue
        
        print(f"\n{'='*50}")
        print(f"Processing: {table_name}")
        print(f"{'='*50}")
        
        success = create_table(table_name)
        
        if success:
            print(f"Successfully set up embedding infrastructure for {table_name}")
        else:
            print(f"Skipped {table_name}")

if __name__ == "__main__":
    discover_and_create_embedding_tables()