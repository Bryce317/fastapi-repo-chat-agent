"""FastAPI dependencies."""

import uuid

from fastapi import Header

from database import get_neo4j_client


async def get_session_id(x_session_id: str | None = Header(None)) -> str:
    """Get or generate session ID from headers.
    
    Args:
        x_session_id: Optional session ID from header.
        
    Returns:
        Session ID.
    """
    return x_session_id or str(uuid.uuid4())


async def verify_neo4j_connection():
    """Verify Neo4j is connected (dependency for routes that need it)."""
    client = await get_neo4j_client()
    return client
