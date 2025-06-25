from openai import OpenAI
import json
import os
import pandas as pd
from dotenv import load_dotenv
from clickhouse_driver import Client
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("API_KEY"))
dbclient = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')

def safe_json_dumps(obj):
    return json.dumps(obj, allow_nan=False)

def clean_sql_query(query_text: str) -> str:
    """Clean SQL query from LLM response"""
    import re
    
    # Remove markdown code blocks
    query_text = re.sub(r'```sql\s*', '', query_text)
    query_text = re.sub(r'```\s*', '', query_text)
    
    lines = query_text.split('\n')
    sql_lines = []
    
    for line in lines:
        line = line.strip()
        if (line.upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'SHOW', 'DESCRIBE', 'CREATE', 'DROP', 'ALTER')) 
            or line.upper().startswith(('FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT'))
            or line.endswith(',') 
            or line.endswith(';')):
            sql_lines.append(line)
    
    return ' '.join(sql_lines).strip()

def apply_query(query):
    """Apply query to ClickHouse and return results with error handling"""
    try:
        clean_query = clean_sql_query(query)
            
        logger.info(f"Executing query: {clean_query}")
        queryresult = dbclient.execute(clean_query)
        
        return {
            "success": True,
            "data": queryresult,
            "row_count": len(queryresult),
            "query": clean_query
        }
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }

async def getquery(prompt: str, context: dict) -> dict:
    """Generate and execute ClickHouse query based on prompt and context"""
    
    schema_info = explore_schema()
    
    context_info = ""
    
    if context:
        if isinstance(context, dict) and 'sample_logs' in context:
            context_info = f"""
                Context from semantic search results:
                - Schema
                - Found {context.get('total_found', 0)} relevant logs
                - Sample log fields: {list(context.get('columns_info', {}).keys())}
                - Example content: {context.get('sample_logs', [])[:2]}
                """
        else:
                context_info = f"Additional context: {context}"
    else:
        context_info = "No prior context available"
        
    system_prompt = f"""
            You are an expert ClickHouse SQL query generator for log analysis. Your task is to create precise, optimized SQL queries based on user requests.

            DATABASE SCHEMA:
            {json.dumps(schema_info, indent=2)}

            {context_info}

            QUERY GENERATION RULES:
            1. ONLY generate SELECT statements (read-only operations)
            2. Use proper ClickHouse syntax and functions
            3. Always include appropriate WHERE clauses for filtering
            4. Use LIMIT to prevent overwhelming results (default LIMIT 100 unless user specifies)
            5. For time-based queries, use proper timestamp formatting
            6. Consider using ClickHouse-specific functions like toHour(), toDate(), etc.
            7. Group and order results logically when doing aggregations
        

            COMMON QUERY PATTERNS:
            - Finding data based on tags: WHERE [COLUMNNAME] = 'ERROR' (Or however the error tag looks based on context given) 
            - Time filtering: WHERE [COLUMNNAME] >= subtractHours(now(), 24)
            - Aggregation: GROUP BY [COLUMNNAME] ORDER BY count() DESC
            - Recent data: ORDER BY timestamp DESC LIMIT 50

            CONTEXT USAGE:
            - If context shows specific field names, use those exact field names
            - If context shows sample values, use those for filtering examples
            - If context indicates patterns, structure query to validate/quantify those patterns (specific tags, keywords, etc.)

            OUTPUT FORMAT:
            Return ONLY the SQL query. Do not include explanations, markdown formatting, or additional text.
            If the request is unclear, generate a reasonable exploratory query. As the Agent will take that as context to come up with a better query.

            """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(prompt)}
            ],
            temperature=0.1  
        )

        generated_query = response.choices[0].message.content.strip()
        logger.info(f"Generated query: {generated_query}")
        
        results = apply_query(generated_query)
        
        return results
        
    except Exception as e:
        logger.error(f"Query generation failed: {e}")
        return {
            "success": False,
            "error": f"Query generation failed: {str(e)}",
            "query": None
        }

def explore_schema():
    """Quick function to explore available data structure"""
    sql = "SHOW TABLES"
    tables = dbclient.execute(sql)
    
    schemacontext = {}
    
    try:
        for name in tables:
            clean_name = str(name).strip()
            if clean_name.startswith("("):
                clean_name = clean_name.replace("(", "").strip()
            if clean_name.endswith(",)"):
                clean_name = clean_name.replace(",)", "").strip()
            print("clean name",clean_name)
            schemacontext[clean_name] = (dbclient.execute(f"DESC {clean_name}"))
            
            return schemacontext
    except Exception as e:
        logger.warning(f"Could not get schema info: {e}")
        return {"error": "Schema info unavailable"}
