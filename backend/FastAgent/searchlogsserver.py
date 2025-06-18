import sys
import os
import asyncio
from mcp.server.fastmcp import FastMCP
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from LlamaIndex.LlamaSearch import search_logs  

mcp = FastMCP("SearchLogsServer")

@mcp.tool()
async def search_logs_tool(prompt: str) -> str:
    """Query logs using LlamaIndex"""
    return await search_logs(prompt)

if __name__ == "__main__":
    mcp.run(transport="stdio")