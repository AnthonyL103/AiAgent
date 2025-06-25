import sys
import os
import asyncio
from mcp.server.fastmcp import FastMCP
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from DataRetrievalTools.QuerySearch import getquery

mcp = FastMCP("QueryLogsServer")
description = """
Execute precise SQL queries directly against the ClickHouse log database with read-only access. This tool provides exact, quantitative analysis of log data with full SQL capabilities for filtering, aggregation, and analysis.

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


INPUT:

-Search_logs_tool takes two arguements, prompt: (str) and context: (dict)
-Apply empty definitions for context if not applicable (ie, {})
"""

name="execute_clickhouse_sql"
@mcp.tool(name,description)
async def search_logs_tool(prompt: str, context: dict) -> dict:
    return await getquery(prompt, context)

if __name__ == "__main__":
    mcp.run(transport="stdio")