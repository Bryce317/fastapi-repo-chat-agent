"""Health check and statistics endpoints."""

from fastapi import APIRouter, Depends

from config.logging_config import get_logger
from core.models import GraphStatistics, HealthCheckResponse
from core.types import EntityType, RelationshipType
from database import get_neo4j_client
from gateway.dependencies import verify_neo4j_connection

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/agents/health", response_model=HealthCheckResponse)
async def check_health() -> HealthCheckResponse:
    """Check health status of all agents and dependencies.
    
    Returns:
        HealthCheckResponse with status of each component.
    """
    # Check Neo4j connection
    neo4j_connected = False
    try:
        client = await get_neo4j_client()
        await client.verify_connectivity()
        neo4j_connected = True
    except Exception as e:
        logger.warning(f"Neo4j health check failed: {e}")
    
    # Check OpenAI (simple check - just verify settings exist)
    from config.settings import get_settings
    settings = get_settings()
    openai_available = bool(settings.openai_api_key)
    
    # All agents are available if code is running
    agents = {
        "orchestrator": True,
        "indexer": True,
        "graph_query": neo4j_connected,  # Requires Neo4j
        "code_analyst": openai_available,  # Requires OpenAI
    }
    
    overall_status = "healthy" if all([neo4j_connected, openai_available]) else "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        agents=agents,
        neo4j_connected=neo4j_connected,
        openai_available=openai_available,
    )


@router.get("/graph/statistics", response_model=GraphStatistics)
async def get_graph_statistics(
    db=Depends(verify_neo4j_connection),
) -> GraphStatistics:
    """Get statistics about the knowledge graph.
    
    Args:
        db: Neo4j database dependency.
        
    Returns:
        GraphStatistics with node and relationship counts.
    """
    try:
        client = await get_neo4j_client()
        
        # Get total counts
        total_nodes = await client.count_nodes()
        total_relationships = await client.count_relationships()
        
        # Get counts by type
        nodes_by_type = {}
        for entity_type in EntityType:
            count = await client.count_nodes(entity_type.value)
            if count > 0:
                nodes_by_type[entity_type.value] = count
        
        relationships_by_type = {}
        for rel_type in RelationshipType:
            count = await client.count_relationships(rel_type.value)
            if count > 0:
                relationships_by_type[rel_type.value] = count
        
        return GraphStatistics(
            total_nodes=total_nodes,
            total_relationships=total_relationships,
            nodes_by_type=nodes_by_type,
            relationships_by_type=relationships_by_type,
        )
        
    except Exception as e:
        logger.error(f"Failed to get graph statistics: {e}")
        # Return empty statistics on error
        return GraphStatistics(
            total_nodes=0,
            total_relationships=0,
            nodes_by_type={},
            relationships_by_type={},
        )
