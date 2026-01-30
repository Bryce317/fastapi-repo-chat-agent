"""Indexing endpoints for repository management."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from agents.indexer.tools import get_indexer_tools
from config.logging_config import get_logger
from core.models import IndexingJob, IndexStatus
from database import get_neo4j_client
from gateway.dependencies import verify_neo4j_connection

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["indexing"])


@router.post("/index")
async def trigger_indexing(
    background_tasks: BackgroundTasks,
    force_reclone: bool = False,
    db=Depends(verify_neo4j_connection),
) -> dict:
    """Trigger repository indexing.
    
    Args:
        background_tasks: FastAPI background tasks.
        force_reclone: Whether to force re-clone the repository.
        db: Neo4j database dependency (ensures connection).
        
    Returns:
        Dictionary with job information.
    """
    try:
        indexer_tools = get_indexer_tools()
        
        # Note: For production, this should use a proper job queue
        # For now, we'll run it directly (blocking)
        logger.info("Starting indexing job...")
        
        result = await indexer_tools.index_repository(force_reclone=force_reclone)
        
        return {
            "message": "Indexing completed",
            **result,
        }
        
    except Exception as e:
        logger.error(f"Indexing trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/status", response_model=IndexStatus)
async def get_indexing_status(
    db=Depends(verify_neo4j_connection),
) -> IndexStatus:
    """Get current indexing status.
    
    Args:
        db: Neo4j database dependency.
        
    Returns:
        IndexStatus with current state.
    """
    try:
        indexer_tools = get_indexer_tools()
        status = await indexer_tools.get_index_status()
        return status
        
    except Exception as e:
        logger.error(f"Failed to get index status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
