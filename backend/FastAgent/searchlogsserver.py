import sys
import os
import asyncio
from mcp.server.fastmcp import FastMCP
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from DataRetrievalTools.LlamaSearch import search_logs_llama

mcp = FastMCP("SearchLogsServer")

description = """
Search through log data using AI-powered semantic understanding via LlamaIndex vector embeddings. This tool excels at finding logs based on meaning, concepts, and context rather than exact text matches.

WHEN TO USE:
- Finding examples of specific issues or behaviors ("authentication problems", "slow database queries")
- Exploring log patterns when you don't know exact error messages
- Understanding what types of logs exist for a particular concept
- Getting sample logs to understand data structure and format
- Discovering related events that share semantic similarity
- Initial exploration when investigating vague user reports

CAPABILITIES:
- Semantic similarity matching (finds "connection timeout" when you search "network issues")
- Time-based filtering to focus on specific periods
- Returns actual log text samples with metadata (timestamp, service, severity)
- Provides context about log structure and available fields
- Handles natural language queries ("show me when users couldn't log in")

BEST FOR:
- Exploratory analysis and pattern discovery
- Finding representative examples of issues
- Understanding log content and structure
- Investigating user-reported problems with unclear descriptions
- Building context before writing precise SQL queries

LIMITATIONS:
- Cannot provide exact counts or statistics
- Limited to similarity-based matching (may miss edge cases)
- Results are sample-based, not comprehensive
- Cannot perform aggregations or mathematical operations
- Needs a table name to work

EXAMPLE QUERIES:
- "authentication failures" → finds login errors, session timeouts, credential issues
- "database problems" → finds connection errors, query timeouts, deadlocks
- "performance issues" → finds slow requests, high CPU usage, memory warnings

INPUT:

-Search_logs takens two arguements, prompt (str) and context: (str)
-Apply empty definitions for context if not applicable (ie, "")
"""

name="search_logs_semantically"
@mcp.tool(name,description)
async def search_logs(prompt: str, context: str) -> dict:
    return await search_logs_llama(prompt, context)

if __name__ == "__main__":
    mcp.run(transport="stdio")