
import asyncio
from mcp_agent.core.fastagent import FastAgent

# Create the FastAgent application
fast = FastAgent("Log Assistant")

@fast.agent(
    name="Dashboard logs/metrics assistant agent",
    instruction="""You are a log analysis assistant with access to two specialized tools. Never include large amounts of data in responses, 
    try to include the important information and summarize the rest.
  
  When analyzing logs, follow this intelligent workflow:
  
  1. **Explore first**: Use SearchLogsServer to understand log patterns
     - "Show me some error logs" → See what error patterns look like
     - Find examples to understand data structure
     - If response is valid enough to answer user question workflow stops here.
  
  2. **Analyze second**: Use QueryLogsServer for structured counting
     - Based on discoveries, do exact queries like "count ERROR logs by service"
     - Use discovered service names, error types for precise filtering
  
  For "How many error logs?":
  - Step 1: Search examples to see error types/services
  - Step 2: Count using exact filters based on what you learned
  """,
    model="gpt-4o",
    servers=["QueryLogsServer","SearchLogsServer"],  
    use_history=True,
    human_input=True
)
async def log_assistant():
    """Main agent function for handling log and metric queries"""
    async with fast.run() as agent:
        await agent()

async def main():
    """Entry point that runs the agent"""
    await log_assistant()

if __name__ == "__main__":
    asyncio.run(main())