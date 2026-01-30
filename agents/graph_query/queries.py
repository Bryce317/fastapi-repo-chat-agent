"""Cypher query builders for Neo4j graph operations."""

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from core.types import EntityType, RelationshipType

logger = get_logger(__name__)


class CypherQueryBuilder:
    """Builder for constructing safe Cypher queries."""

    @staticmethod
    def find_entity_by_name(name: str, entity_type: Optional[EntityType] = None) -> tuple[str, Dict[str, Any]]:
        """Build query to find entity by name.
        
        Args:
            name: Entity name (can be partial for fuzzy search).
            entity_type: Optional entity type filter.
            
        Returns:
            Tuple of (query, parameters).
        """
        if entity_type:
            query = f"""
                MATCH (e:{entity_type.value})
                WHERE e.name CONTAINS $name
                RETURN e
                LIMIT 50
            """
        else:
            query = """
                MATCH (e)
                WHERE e.name CONTAINS $name
                RETURN e, labels(e) as entity_type
                LIMIT 50
            """
        
        return query, {"name": name}

    @staticmethod
    def get_dependencies(entity_name: str) -> tuple[str, Dict[str, Any]]:
        """Build query to find what an entity depends on.
        
        Args:
            entity_name: Name of the entity.
            
        Returns:
            Tuple of (query, parameters).
        """
        query = """
            MATCH (e {name: $name})-[r:IMPORTS|DEPENDS_ON|CALLS]->(target)
            RETURN target, type(r) as relationship_type
            LIMIT 100
        """
        
        return query, {"name": entity_name}

    @staticmethod
    def get_dependents(entity_name: str) -> tuple[str, Dict[str, Any]]:
        """Build query to find what depends on an entity.
        
        Args:
            entity_name: Name of the entity.
            
        Returns:
            Tuple of (query, parameters).
        """
        query = """
            MATCH (source)-[r:IMPORTS|DEPENDS_ON|CALLS]->(e {name: $name})
            RETURN source, type(r) as relationship_type
            LIMIT 100
        """
        
        return query, {"name": entity_name}

    @staticmethod
    def trace_imports(module_name: str, max_depth: int = 3) -> tuple[str, Dict[str, Any]]:
        """Build query to trace import chain for a module.
        
        Args:
            module_name: Module name.
            max_depth: Maximum depth to traverse.
            
        Returns:
            Tuple of (query, parameters).
        """
        query = f"""
            MATCH path = (m:Module {{name: $name}})-[:IMPORTS*1..{max_depth}]->(imported)
            RETURN path
            LIMIT 50
        """
        
        return query, {"name": module_name}

    @staticmethod
    def find_related(
        entity_name: str, 
        relationship_type: RelationshipType,
        direction: str = "outgoing"
    ) -> tuple[str, Dict[str, Any]]:
        """Build query to find entities related by specific relationship.
        
        Args:
            entity_name: Name of the entity.
            relationship_type: Type of relationship.
            direction: "outgoing", "incoming", or "both".
            
        Returns:
            Tuple of (query, parameters).
        """
        if direction == "outgoing":
            query = f"""
                MATCH (e {{name: $name}})-[r:{relationship_type.value}]->(related)
                RETURN related, r
                LIMIT 100
            """
        elif direction == "incoming":
            query = f"""
                MATCH (related)-[r:{relationship_type.value}]->(e {{name: $name}})
                RETURN related, r
                LIMIT 100
            """
        else:  # both
            query = f"""
                MATCH (e {{name: $name}})-[r:{relationship_type.value}]-(related)
                RETURN related, r
                LIMIT 100
            """
        
        return query, {"name": entity_name}

    @staticmethod
    def find_inheritance_hierarchy(class_name: str) -> tuple[str, Dict[str, Any]]:
        """Build query to find class inheritance hierarchy.
        
        Args:
            class_name: Name of the class.
            
        Returns:
            Tuple of (query, parameters).
        """
        query = """
            // Find parent classes
            MATCH path1 = (c:Class {name: $name})-[:INHERITS_FROM*]->(parent)
            
            // Find child classes
            OPTIONAL MATCH path2 = (child)-[:INHERITS_FROM*]->(c)
            
            RETURN path1, path2
            LIMIT 50
        """
        
        return query, {"name": class_name}

    @staticmethod
    def find_function_calls(function_name: str) -> tuple[str, Dict[str, Any]]:
        """Build query to find all calls to/from a function.
        
        Args:
            function_name: Name of the function.
            
        Returns:
            Tuple of (query, parameters).
        """
        query = """
            // Functions this one calls
            MATCH (f {name: $name})-[:CALLS]->(called)
            RETURN 'calls' as direction, called
            
            UNION
            
            // Functions that call this one
            MATCH (caller)-[:CALLS]->(f {name: $name})
            RETURN 'called_by' as direction, caller
            
            LIMIT 100
        """
        
        return query, {"name": function_name}

    @staticmethod
    def find_decorated_entities(decorator_name: str) -> tuple[str, Dict[str, Any]]:
        """Build query to find all entities with a specific decorator.
        
        Args:
            decorator_name: Name of the decorator.
            
        Returns:
            Tuple of (query, parameters).
        """
        query = """
            MATCH (entity)-[:DECORATED_BY]->(d:Decorator)
            WHERE d.name = $decorator OR d.name CONTAINS $decorator
            RETURN entity, labels(entity) as entity_type
            LIMIT 100
        """
        
        return query, {"decorator": decorator_name}

    @staticmethod
    def get_module_structure(module_name: str) -> tuple[str, Dict[str, Any]]:
        """Build query to get complete structure of a module.
        
        Args:
            module_name: Module name.
            
        Returns:
            Tuple of (query, parameters).
        """
        query = """
            MATCH (m:Module {name: $name})
            OPTIONAL MATCH (m)-[:CONTAINS]->(entity)
            RETURN m, collect(entity) as entities
        """
        
        return query, {"name": module_name}

    @staticmethod
    def search_by_docstring(search_term: str) -> tuple[str, Dict[str, Any]]:
        """Build query to search entities by docstring content.
        
        Args:
            search_term: Search term to look for in docstrings.
            
        Returns:
            Tuple of (query, parameters).
        """
        query = """
            MATCH (entity)
            WHERE entity.docstring CONTAINS $term
            RETURN entity, labels(entity) as entity_type, entity.docstring as docstring
            LIMIT 50
        """
        
        return query, {"term": search_term}

    @staticmethod
    def validate_query(query: str) -> bool:
        """Validate that a Cypher query is safe to execute.
        
        Args:
            query: Cypher query string.
            
        Returns:
            True if query is safe, False otherwise.
        """
        # Blacklist dangerous operations
        dangerous_keywords = [
            "DELETE",
            "DETACH DELETE",
            "REMOVE",
            "SET",
            "CREATE CONSTRAINT",
            "DROP",
        ]
        
        query_upper = query.upper()
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                logger.warning(f"Dangerous keyword '{keyword}' found in query")
                return False
        
        return True
