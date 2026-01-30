"""Chat endpoint for conversational interactions."""

from fastapi import APIRouter, Depends, HTTPException

from agents.orchestrator.graph import get_orchestrator_graph
from config.logging_config import get_logger
from core.models import ChatRequest, ChatResponse
from core.types import AgentType
from gateway.dependencies import get_session_id
from memory import get_conversation_memory

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session_id: str = Depends(get_session_id),
) -> ChatResponse:
    """Process a chat message and return response.
    
    Args:
        request: Chat request with user message.
        session_id: Session ID from dependency.
        
    Returns:
        ChatResponse with assistant's reply.
    """
    try:
        # Use session_id from request if provided, otherwise from dependency
        final_session_id = request.session_id or session_id
        
        logger.info(f"Processing chat request for session {final_session_id}")
        
        # Get conversation history
        conversation_memory = get_conversation_memory()
        history = conversation_memory.format_for_llm(final_session_id, last_n=10)
        
        # Process query through orchestrator
        orchestrator = get_orchestrator_graph()
        result = await orchestrator.process_query(
            query=request.message,
            session_id=final_session_id,
            conversation_history=history,
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to process query"),
            )
        
        return ChatResponse(
            response=result["response"],
            session_id=final_session_id,
            agents_used=result.get("agents_used", []),
            processing_time=result.get("processing_time", 0.0),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
