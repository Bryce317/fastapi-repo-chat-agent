"""Neo4j graph schema initialization for FastAPI codebase."""

from typing import List

from config.logging_config import get_logger
from core.types import EntityType, RelationshipType

from .neo4j_client import Neo4jClient

logger = get_logger(__name__)


# Schema definition for node labels and their properties
NODE_SCHEMAS = {
    EntityType.FILE: ["path", "name", "size", "last_modified"],
    EntityType.MODULE: ["name", "path", "docstring"],
    EntityType.CLASS: ["name", "docstring", "line_number", "is_abstract"],
    EntityType.FUNCTION: ["name", "docstring", "line_number", "is_async", "signature"],
    EntityType.METHOD: ["name", "docstring", "line_number", "is_async", "is_static", "is_classmethod", "signature"],
    EntityType.PARAMETER: ["name", "type_annotation", "default_value", "position"],
    EntityType.DECORATOR: ["name", "arguments"],
    EntityType.IMPORT: ["module_name", "imported_names", "is_from_import"],
    EntityType.DOCSTRING: ["content", "line_number"],
}


async def initialize_schema(client: Neo4jClient) -> None:
    """Initialize Neo4j schema with constraints and indexes.
    
    Args:
        client: Neo4j client instance.
    """
    logger.info("Initializing Neo4j schema...")
    
    # Create constraints for unique identifiers
    constraints = [
        # File nodes must have unique paths
        f"CREATE CONSTRAINT file_path_unique IF NOT EXISTS "
        f"FOR (f:{EntityType.FILE.value}) REQUIRE f.path IS UNIQUE",
        
        # Module nodes identified by path
        f"CREATE CONSTRAINT module_path_unique IF NOT EXISTS "
        f"FOR (m:{EntityType.MODULE.value}) REQUIRE m.path IS UNIQUE",
        
        # Class nodes identified by name + module path
        f"CREATE CONSTRAINT class_name_path_unique IF NOT EXISTS "
        f"FOR (c:{EntityType.CLASS.value}) REQUIRE (c.name, c.module_path) IS UNIQUE",
        
        # Function nodes identified by name + module path
        f"CREATE CONSTRAINT function_name_path_unique IF NOT EXISTS "
        f"FOR (f:{EntityType.FUNCTION.value}) REQUIRE (f.name, f.module_path) IS UNIQUE",
    ]
    
    for constraint in constraints:
        try:
            await client.execute_write(constraint)
            logger.debug(f"Created constraint: {constraint[:50]}...")
        except Exception as e:
            # Constraint might already exist
            logger.debug(f"Constraint creation skipped (may already exist): {e}")
    
    # Create indexes for frequently queried properties
    indexes = [
        # Index on file names for quick lookup
        f"CREATE INDEX file_name_index IF NOT EXISTS "
        f"FOR (f:{EntityType.FILE.value}) ON (f.name)",
        
        # Index on module names
        f"CREATE INDEX module_name_index IF NOT EXISTS "
        f"FOR (m:{EntityType.MODULE.value}) ON (m.name)",
        
        # Index on class names for searching
        f"CREATE INDEX class_name_index IF NOT EXISTS "
        f"FOR (c:{EntityType.CLASS.value}) ON (c.name)",
        
        # Index on function names
        f"CREATE INDEX function_name_index IF NOT EXISTS "
        f"FOR (f:{EntityType.FUNCTION.value}) ON (f.name)",
        
        # Index on method names
        f"CREATE INDEX method_name_index IF NOT EXISTS "
        f"FOR (m:{EntityType.METHOD.value}) ON (m.name)",
        
        # Index on decorator names
        f"CREATE INDEX decorator_name_index IF NOT EXISTS "
        f"FOR (d:{EntityType.DECORATOR.value}) ON (d.name)",
    ]
    
    for index in indexes:
        try:
            await client.execute_write(index)
            logger.debug(f"Created index: {index[:50]}...")
        except Exception as e:
            logger.debug(f"Index creation skipped (may already exist): {e}")
    
    logger.info("Schema initialization completed")


async def clear_database(client: Neo4jClient) -> None:
    """Clear all nodes and relationships from the database.
    
    WARNING: This will delete ALL data in the database!
    
    Args:
        client: Neo4j client instance.
    """
    logger.warning("Clearing Neo4j database...")
    
    # Delete all relationships first
    await client.execute_write("MATCH ()-[r]->() DELETE r")
    
    # Then delete all nodes
    await client.execute_write("MATCH (n) DELETE n")
    
    # Verify deletion
    node_count = await client.count_nodes()
    rel_count = await client.count_relationships()
    
    logger.info(f"Database cleared. Nodes: {node_count}, Relationships: {rel_count}")


async def get_schema_info(client: Neo4jClient) -> dict:
    """Get information about the current schema.
    
    Args:
        client: Neo4j client instance.
        
    Returns:
        Dictionary with schema information.
    """
    # Get all node labels
    labels_query = "CALL db.labels()"
    labels_result = await client.execute_read(labels_query)
    labels = [record["label"] for record in labels_result]
    
    # Get all relationship types
    rel_types_query = "CALL db.relationshipTypes()"
    rel_types_result = await client.execute_read(rel_types_query)
    rel_types = [record["relationshipType"] for record in rel_types_result]
    
    # Get constraints
    constraints_query = "SHOW CONSTRAINTS"
    try:
        constraints_result = await client.execute_read(constraints_query)
        constraints = [record.get("name", "Unknown") for record in constraints_result]
    except Exception:
        constraints = []
    
    # Get indexes
    indexes_query = "SHOW INDEXES"
    try:
        indexes_result = await client.execute_read(indexes_query)
        indexes = [record.get("name", "Unknown") for record in indexes_result]
    except Exception:
        indexes = []
    
    return {
        "node_labels": labels,
        "relationship_types": rel_types,
        "constraints": constraints,
        "indexes": indexes,
    }
