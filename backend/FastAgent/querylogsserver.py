import sys
import os
import asyncio
from mcp.server.fastmcp import FastMCP
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from DataRetrievalTools.QuerySearch import getquery

mcp = FastMCP("QueryLogsServer")

@mcp.tool(description= "Query logs using structured filters. Best for querying logs via structured filtering for aggregation, timestamp, and exact queries. You are supposed pass detailed context about logs to this tool such as certain flags, keywords, and structure which you can get from the searchlogserver.")
async def search_logs_tool(prompt: str, context: dict = None) -> str:
    print(context)
    return await getquery(prompt, context)

if __name__ == "__main__":
    mcp.run(transport="stdio")