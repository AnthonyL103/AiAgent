from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from FastAgent.agent import fast
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self):
        self.agent = None
        self.agent_context = None
    
    async def start(self):
        """Start persistent agent context"""
        if not self.agent_context:
            logger.info("Starting persistent agent context...")
            self.agent_context = fast.run()
            self.agent = await self.agent_context.__aenter__()
            logger.info("Agent context started successfully")
    
    async def stop(self):
        """Stop agent context"""
        if self.agent_context:
            logger.info("Stopping agent context...")
            await self.agent_context.__aexit__(None, None, None)
            self.agent_context = None
            self.agent = None
            logger.info("Agent context stopped")
    
    async def chat(self, message: str):
        """Send message to persistent agent and get immediate response"""
        if not self.agent:
            await self.start()
        
        logger.info(f"Sending message to agent: {message}")
        result = await self.agent(message)
        logger.info("Received response from agent")
        return result

chat_manager = ChatManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await chat_manager.start()
        logger.info("FastAPI app started with persistent agent")
        yield
    finally:
        await chat_manager.stop()
        logger.info("FastAPI app shutdown complete")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str

class PromptResponse(BaseModel):
    result: str
    status: str = "success"

@app.post("/get_prompt", response_model=PromptResponse)
async def search_logs(prompt_request: PromptRequest):
    """
    Process user query with persistent conversation context.
    Returns immediate response while maintaining chat history.
    """
    try:
        user_query = prompt_request.prompt
        
        if not user_query.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        logger.info(f"Processing query: {user_query}")
        
        result = await chat_manager.chat(user_query)
        
        logger.info("Query processed successfully")
        
        return PromptResponse(result=result)
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/reset_conversation")
async def reset_conversation():
    """Reset the conversation history while keeping the agent running"""
    try:
        logger.info("Resetting conversation...")
        await chat_manager.stop()
        await chat_manager.start()
        logger.info("Conversation reset successfully")
        return {"status": "success", "message": "Conversation history reset"}
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resetting conversation: {str(e)}")

@app.get("/health")
async def health_check():
    """Check if the app and agent are healthy"""
    try:
        if chat_manager.agent:
            return {"status": "healthy", "agent_status": "running"}
        else:
            return {"status": "healthy", "agent_status": "not_initialized"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/agent_status")
async def agent_status():
    """Get detailed agent status"""
    return {
        "agent_initialized": chat_manager.agent is not None,
        "context_active": chat_manager.agent_context is not None,
        "status": "ready" if chat_manager.agent else "not_ready"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)