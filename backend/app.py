from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from FastAgent.agent import fast
import asyncio
import logging
import json
import uuid
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self):
        self.agent = None
        self.agent_context = None
        self.pending_human_inputs: Dict[str, Dict] = {}
    
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
    
    def is_human_input_request(self, result: Any) -> bool:
        """Check if the result contains a human input request"""
        # Convert result to string to analyze
        result_str = str(result)
        
        # Look for common human input request patterns
        human_input_indicators = [
            "HUMAN INPUT REQUESTED",
            "__human_input_request",
            "Need user input",
            "Could you please specify",
            "Please provide",
            "Human response:",
            "Type /help for commands"
        ]
        
        return any(indicator in result_str for indicator in human_input_indicators)
    
    def extract_human_input_prompt(self, result: Any) -> Optional[str]:
        """Extract the human input prompt from the result"""
        result_str = str(result)
        
        # Try to extract the actual question being asked
        lines = result_str.split('\n')
        
        for line in lines:
            line = line.strip()
            if ('?' in line and 
                ('specify' in line.lower() or 
                 'provide' in line.lower() or 
                 'enter' in line.lower() or
                 'what' in line.lower())):
                # Clean up the line
                cleaned = line.replace('│', '').replace('╭', '').replace('╰', '').strip()
                if cleaned:
                    return cleaned
        
        # Fallback to a generic prompt
        return "Please provide additional information:"
    
    async def chat(self, message: str) -> Dict[str, Any]:
        """Send message to persistent agent and get immediate response"""
        if not self.agent:
            await self.start()
        
        logger.info(f"Sending message to agent: {message}")
        result = await self.agent(message)
        logger.info("Received response from agent")
        
        # Check if this is a human input request
        if self.is_human_input_request(result):
            logger.info("Detected human input request")
            
            # Generate a unique request ID
            request_id = str(uuid.uuid4())
            
            # Extract the prompt
            prompt = self.extract_human_input_prompt(result)
            
            # Store the request for later continuation
            self.pending_human_inputs[request_id] = {
                "original_query": message,
                "agent_response": result,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            return {
                "type": "human_input_required",
                "request_id": request_id,
                "prompt": prompt,
                "description": "The agent needs additional information to continue.",
                "original_response": str(result)
            }
        
        # Normal response
        return {
            "type": "normal_response",
            "result": str(result)
        }
    
    async def submit_human_input(self, request_id: str, user_input: str) -> Dict[str, Any]:
        """Submit human input and continue the conversation"""
        if request_id not in self.pending_human_inputs:
            raise ValueError("Invalid or expired request ID")
        
        pending_request = self.pending_human_inputs[request_id]
        logger.info(f"Submitting human input: {user_input}")
        
        # Send the human input to the agent
        result = await self.agent(user_input)
        
        # Clean up pending request
        del self.pending_human_inputs[request_id]
        
        # Check if this triggers another human input request
        if self.is_human_input_request(result):
            logger.info("Another human input request detected")
            
            new_request_id = str(uuid.uuid4())
            prompt = self.extract_human_input_prompt(result)
            
            self.pending_human_inputs[new_request_id] = {
                "original_query": user_input,
                "agent_response": result,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            return {
                "type": "human_input_required",
                "request_id": new_request_id,
                "prompt": prompt,
                "description": "The agent needs additional information to continue.",
                "original_response": str(result)
            }
        
        return {
            "type": "normal_response",
            "result": str(result)
        }

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

class HumanInputRequest(BaseModel):
    request_id: str
    user_input: str

class PromptResponse(BaseModel):
    result: Optional[str] = None
    status: str = "success"
    type: str = "normal_response"
    request_id: Optional[str] = None
    prompt: Optional[str] = None
    description: Optional[str] = None

@app.post("/get_prompt", response_model=PromptResponse)
async def search_logs(prompt_request: PromptRequest):
    """
    Process user query with persistent conversation context.
    Returns immediate response or human input request.
    """
    try:
        user_query = prompt_request.prompt
        
        if not user_query.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        logger.info(f"Processing query: {user_query}")
        
        result = await chat_manager.chat(user_query)
        
        if result["type"] == "human_input_required":
            logger.info("Returning human input request to frontend")
            return PromptResponse(
                type="human_input_required",
                request_id=result["request_id"],
                prompt=result["prompt"],
                description=result["description"],
                status="requires_input"
            )
        else:
            logger.info("Query processed successfully")
            return PromptResponse(
                result=result["result"],
                type="normal_response"
            )
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/submit_human_input")
async def submit_human_input(input_request: HumanInputRequest):
    """Submit human input and continue the conversation"""
    try:
        logger.info(f"Submitting human input for request {input_request.request_id}")
        
        result = await chat_manager.submit_human_input(
            input_request.request_id, 
            input_request.user_input
        )
        
        if result["type"] == "human_input_required":
            return PromptResponse(
                type="human_input_required",
                request_id=result["request_id"],
                prompt=result["prompt"],
                description=result["description"],
                status="requires_input"
            )
        else:
            return PromptResponse(
                result=result["result"],
                type="normal_response"
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting human input: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error submitting human input: {str(e)}")

@app.get("/pending_requests")
async def get_pending_requests():
    """Get list of pending human input requests"""
    return {
        "pending_requests": list(chat_manager.pending_human_inputs.keys()),
        "count": len(chat_manager.pending_human_inputs)
    }

@app.post("/reset_conversation")
async def reset_conversation():
    """Reset the conversation history while keeping the agent running"""
    try:
        logger.info("Resetting conversation...")
        chat_manager.pending_human_inputs.clear()
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
        "status": "ready" if chat_manager.agent else "not_ready",
        "pending_inputs": len(chat_manager.pending_human_inputs)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)