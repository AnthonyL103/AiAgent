import sys
import os
import asyncio
from mcp.server.fastmcp import FastMCP
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from DataRetrievalTools.LlamaSearch import search_logs_llama

mcp = FastMCP("SearchLogsServer")

@mcp.tool(description="Search logs semantically using LlamaIndex, with ability to filter by time. Good for finding examples semantically and providing context of logs and log structure.")
async def search_logs(prompt: str) -> dict:
    return await search_logs_llama(prompt)

if __name__ == "__main__":
    mcp.run(transport="stdio")