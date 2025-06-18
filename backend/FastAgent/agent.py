
import asyncio
from mcp_agent.core.fastagent import FastAgent

# Create the FastAgent application
fast = FastAgent("Log Assistant")

@fast.agent(
    name="Dashboard logs/metrics assistant agent",
    instruction="Use tools available to answer user queries about logs and metrics. If you don't know the answer, say 'I don't know'.",
    model="gpt-4o",
    servers=["search_logs"],  
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