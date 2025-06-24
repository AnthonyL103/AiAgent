
import asyncio
from mcp_agent.core.fastagent import FastAgent

# Create the FastAgent application
fast = FastAgent("Log Assistant")

@fast.agent(
    name="Dashboard logs/metrics assistant agent",
    instruction="""You are a log analysis assistant with access to specialized tools. Never include large amounts of data in responses, 
    try to include the important information and summarize the rest. Use good formatting in your responses, make it structured and easy to read.
  

  """,
    model="gpt-4o",
    servers=["SearchLogsServer"],  
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