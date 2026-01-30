"""Graph Query agent tools for MCP server."""

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from core.exceptions import GraphQueryError
from core.types import EntityType, RelationshipType
from database import get_neo4j_client
from utils.helpers import parse_cypher_result

from .queries import CypherQueryBuilder

logger = get_logger(__name__)


class GraphQueryTools:
    """MCP tools for the Graph Query agent."""

    def __init__(self):
        """Initialize graph query tools."""
        self.query_builder = CypherQueryBuilder()

    async def find_entity(
        self, 
        name: str, 
        entity_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Find entities by name.
        
        Args:
            name: Entity name (supports partial matching).
            entity_type: Optional entity type filter.
            
        Returns:
            Dictionary with search results.
        """
        try:
            neo4j_client = await get_neo4j_client()
            
            # Convert entity_type string to enum
            entity_type_enum = EntityType(entity_type) if entity_type else None
            
            query, params = self.query_builder.find_entity_by_name(name, entity_type_enum)
            result = await neo4j_client.execute_read(query, params)
            
            logger.debug(f"Found {len(result)} entities matching '{name}'")
            
            return {
                "success": True,
                "query": name,
                "entity_type": entity_type,
                "results": parse_cypher_result(result),
                "count": len(result),
            }
            
        except Exception as e:
            logger.error(f"Failed to find entity: {e}")
            raise GraphQueryError(f"Entity search failed: {e}")

    async def get_dependencies(self, entity_name: str) -> Dict[str, Any]:
        """Get what an entity depends on.
        
        Args:
            entity_name: Name of the entity.
            
        Returns:
            Dictionary with dependencies.
        """
        try:
            neo4j_client = await get_neo4j_client()
            
            query, params = self.query_builder.get_dependencies(entity_name)
            result = await neo4j_client.execute_read(query, params)
            
            logger.debug(f"Found {len(result)} dependencies for '{entity_name}'")
            
            return {
                "success": True,
                "entity": entity_name,
                "dependencies": parse_cypher_result(result),
                "count": len(result),
            }
            
        except Exception as e:
            logger.error(f"Failed to get dependencies: {e}")
            raise GraphQueryError(f"Dependency query failed: {e}")

    async def get_dependents(self, entity_name: str) -> Dict[str, Any]:
        """Get what depends on an entity.
        
        Args:
            entity_name: Name of the entity.
            
        Returns:
            Dictionary with dependents.
        """
        try:
            neo4j_client = await get_neo4j_client()
            
            query, params = self.query_builder.get_dependents(entity_name)
            result = await neo4j_client.execute_read(query, params)
            
            logger.debug(f"Found {len(result)} dependents for '{entity_name}'")
            
            return {
                "success": True,
                "entity": entity_name,
                "dependents": parse_cypher_result(result),
                "count": len(result),
            }
            
        except Exception as e:
            logger.error(f"Failed to get dependents: {e}")
            raise GraphQueryError(f"Dependent query failed: {e}")

    async def trace_imports(
        self, 
        module_name: str, 
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """Trace import chain for a module.
        
        Args:
            module_name: Module name.
            max_depth: Maximum depth to traverse.
            
        Returns:
            Dictionary with import chain.
        """
        try:
            neo4j_client = await get_neo4j_client()
            
            query, params = self.query_builder.trace_imports(module_name, max_depth)
            result = await neo4j_client.execute_read(query, params)
            
            logger.debug(f"Found {len(result)} import paths for '{module_name}'")
            
            return {
                "success": True,
                "module": module_name,
                "max_depth": max_depth,
                "import_paths": parse_cypher_result(result),
                "count": len(result),
            }
            
        except Exception as e:
            logger.error(f"Failed to trace imports: {e}")
            raise GraphQueryError(f"Import trace failed: {e}")

    async def find_related(
        self,
        entity_name: str,
        relationship_type: str,
        direction: str = "outgoing"
    ) -> Dict[str, Any]:
        """Find entities related by specific relationship.
        
        Args:
            entity_name: Name of the entity.
            relationship_type: Type of relationship.
            direction: "outgoing", "incoming", or "both".
            
        Returns:
            Dictionary with related entities.
        """
        try:
            neo4j_client = await get_neo4j_client()
            
            rel_type_enum = RelationshipType(relationship_type)
            
            query, params = self.query_builder.find_related(
                entity_name, rel_type_enum, direction
            )
            result = await neo4j_client.execute_read(query, params)
            
            logger.debug(
                f"Found {len(result)} entities related to '{entity_name}' "
                f"via {relationship_type}"
            )
            
            return {
                "success": True,
                "entity": entity_name,
                "relationship_type": relationship_type,
                "direction": direction,
                "related_entities": parse_cypher_result(result),
                "count": len(result),
            }
            
        except Exception as e:
            logger.error(f"Failed to find related entities: {e}")
            raise GraphQueryError(f"Related entity query failed: {e}")

    async def execute_query(self, cypher_query: str) -> Dict[str, Any]:
        """Execute a custom Cypher query (with safety checks).
        
        Args:
            cypher_query: Cypher query string.
            
        Returns:
            Dictionary with query results.
        """
        try:
            # Validate query for safety
            if not self.query_builder.validate_query(cypher_query):
                raise GraphQueryError("Query contains dangerous operations")
            
            neo4j_client = await get_neo4j_client()
            result = await neo4j_client.execute_read(cypher_query)
            
            logger.debug(f"Custom query returned {len(result)} results")
            
            return {
                "success": True,
                "query": cypher_query,
                "results": parse_cypher_result(result),
                "count": len(result),
            }
            
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise GraphQueryError(f"Query execution failed: {e}")

    async def get_inheritance_hierarchy(self, class_name: str) -> Dict[str, Any]:
        """Get class inheritance hierarchy.
        
        Args:
            class_name: Name of the class.
            
        Returns:
            Dictionary with hierarchy information.
        """
        try:
            neo4j_client = await get_neo4j_client()
            
            query, params = self.query_builder.find_inheritance_hierarchy(class_name)
            result = await neo4j_client.execute_read(query, params)
            
            logger.debug(f"Found inheritance hierarchy for '{class_name}'")
            
            return {
                "success": True,
                "class": class_name,
                "hierarchy": parse_cypher_result(result),
            }
            
        except Exception as e:
            logger.error(f"Failed to get inheritance hierarchy: {e}")
            raise GraphQueryError(f"Inheritance query failed: {e}")


# Global graph query tools instance
_graph_query_tools: GraphQueryTools | None = None


def get_graph_query_tools() -> GraphQueryTools:
    """Get or create global GraphQueryTools instance.
    
    Returns:
        GraphQueryTools instance.
    """
    global _graph_query_tools
    
    if _graph_query_tools is None:
        _graph_query_tools = GraphQueryTools()
    
    return _graph_query_tools
