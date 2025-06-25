import sys
import os
import asyncio
from mcp.server.fastmcp import FastMCP
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from DataRetrievalTools.QuerySearch import apply_query
from clickhouse_driver import Client

mcp = FastMCP("QueryLogsServer")

dbclient = Client(host='localhost', port=9000, user='AgentDemo', password='ILoveAgents45867760')


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
        return {"error": "Schema info unavailable"}
    
Schema = explore_schema()
    
description = """
Execute precise SQL queries directly against the ClickHouse log database with read-only access. This tool provides exact, quantitative analysis of log data with full SQL capabilities for filtering, aggregation, and analysis.

Current Schema:

{Schema}

INPUT REQUIREMENTS:

-Function takes one arguement, prompt: (str) 

Correct Call:

search_logs_tool("some prompt")

Incorrect Call:

search_logs_tool()

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
            - If you have context that shows specific field names, use those exact field names
            - If you have context shows sample values, use those for filtering examples
            - If you have context that indicates patterns, structure query to validate/quantify those patterns (specific tags, keywords, etc.)

            OUTPUT FORMAT:
            INPUT ONLY the SQL query. Do not include explanations, markdown formatting, or additional text.
            If the request is unclear, generate a reasonable exploratory query. As you can take that as context to come up with a better query.


WHEN TO USE:
- Getting exact counts, statistics, and metrics
- Performing time-series analysis and trend identification
- Complex filtering with multiple conditions
- Aggregating data by services, severity levels, or time periods
- Exploring database schema and understanding available data
- Validating patterns discovered through semantic search
- Answering "how many", "when exactly", "which services" type questions

CAPABILITIES:
- Full SQL SELECT operations (GROUP BY, ORDER BY, WHERE, HAVING, etc.)
- Schema exploration (SHOW TABLES, DESCRIBE tables, column inspection)
- Time-based filtering with precise date/time ranges
- Statistical functions (COUNT, SUM, AVG, percentiles)
- Complex joins and subqueries if multiple tables exist
- Window functions for advanced analytics

RECOMMENDED WORKFLOW:
1. Start with schema exploration if unfamiliar with data structure
2. Use semantic search results to inform precise SQL filtering conditions
3. Build iterative queries: start simple, add complexity based on results
4. Cross-validate findings with semantic search examples

SCHEMA DISCOVERY QUERIES:
- SHOW TABLES → see available tables
- DESCRIBE table_name → understand column structure
- SELECT DISTINCT column_name FROM table LIMIT 10 → see sample values
- SELECT COUNT(*) FROM table WHERE timestamp > date_sub(now(), interval 1 hour) → recent data volume

ANALYSIS PATTERNS:
- Error analysis: WHERE SeverityText = 'ERROR' AND timestamp BETWEEN...
- Service performance: GROUP BY ServiceName ORDER BY COUNT(*) DESC
- Time trends: GROUP BY toHour(timestamp) for hourly patterns
- Correlation analysis: Compare events across timeframes and services

BEST FOR:
- Quantitative analysis and precise measurements
- Trend analysis over time periods
- Comparative analysis between services or time periods
- Validating hypotheses with concrete data
- Building dashboards or reports with exact metrics

LIMITATIONS:
- Read-only access (no INSERT, UPDATE, DELETE operations)
- Requires knowledge of SQL syntax and database schema
- Cannot understand context or meaning like semantic search
- Less effective for exploratory "what happened?" investigations without specific criteria

EXAMPLE WORKFLOWS:
1. EXPLORE: "SHOW TABLES" → "DESCRIBE logs" → understand available data
2. QUANTIFY: Use semantic search findings to build targeted WHERE clauses
3. ANALYZE: "SELECT ServiceName, COUNT(*) FROM logs WHERE SeverityText='ERROR' AND timestamp > now() - interval 24 hour GROUP BY ServiceName"
4. VALIDATE: Cross-check SQL results against semantic search examples



"""

name="execute_clickhouse_sql"
@mcp.tool(name,description)
async def search_logs_tool(prompt: str) -> dict:
    return await apply_query(prompt)

if __name__ == "__main__":
    mcp.run(transport="stdio")