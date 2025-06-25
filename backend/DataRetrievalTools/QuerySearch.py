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

async def apply_query(query):
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
