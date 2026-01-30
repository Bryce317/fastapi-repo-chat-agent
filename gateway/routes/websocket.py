"""WebSocket endpoint for real-time chat."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agents.orchestrator.graph import get_orchestrator_graph
from config.logging_config import get_logger
from memory import get_conversation_memory

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with streaming.
    
    Args:
        websocket: WebSocket connection.
    """
    await websocket.accept()
    
    # Generate session ID for this connection
    import uuid
    session_id = str(uuid.uuid4())
    
    logger.info(f"WebSocket connection established: {session_id}")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to FastAPI Chat Agent",
            "session_id": session_id,
        })
        
        conversation_memory = get_conversation_memory()
        orchestrator = get_orchestrator_graph()
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                user_message = message_data.get("message", "")
                
                if not user_message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty message received",
                    })
                    continue
                
                logger.info(f"WebSocket message received: {user_message[:50]}...")
                
                # Send acknowledgment
                await websocket.send_json({
                    "type": "processing",
                    "message": "Processing your message...",
                })
                
                # Get conversation history
                history = conversation_memory.format_for_llm(session_id, last_n=10)
                
                # Process query
                result = await orchestrator.process_query(
                    query=user_message,
                    session_id=session_id,
                    conversation_history=history,
                )
                
                # Send response
                await websocket.send_json({
                    "type": "response",
                    "message": result["response"],
                    "agents_used": [a.value for a in result.get("agents_used", [])],
                    "processing_time": result.get("processing_time", 0.0),
                })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
