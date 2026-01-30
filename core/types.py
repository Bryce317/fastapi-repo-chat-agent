"""Type definitions and enums for the multi-agent system."""

from enum import Enum


class AgentType(str, Enum):
    """Enum for different agent types in the system."""

    ORCHESTRATOR = "orchestrator"
    INDEXER = "indexer"
    GRAPH_QUERY = "graph_query"
    CODE_ANALYST = "code_analyst"


class QueryType(str, Enum):
    """Enum for query complexity classification."""

    SIMPLE = "simple"  # Single agent, simple lookup
    MEDIUM = "medium"  # 2-3 agents, moderate complexity
    COMPLEX = "complex"  # Multiple agents, synthesis required


class EntityType(str, Enum):
    """Enum for code entity types in the knowledge graph."""

    MODULE = "Module"
    CLASS = "Class"
    FUNCTION = "Function"
    METHOD = "Method"
    PARAMETER = "Parameter"
    DECORATOR = "Decorator"
    IMPORT = "Import"
    DOCSTRING = "Docstring"
    FILE = "File"


class RelationshipType(str, Enum):
    """Enum for relationship types in the knowledge graph."""

    CONTAINS = "CONTAINS"
    IMPORTS = "IMPORTS"
    INHERITS_FROM = "INHERITS_FROM"
    CALLS = "CALLS"
    DECORATED_BY = "DECORATED_BY"
    HAS_PARAMETER = "HAS_PARAMETER"
    DOCUMENTED_BY = "DOCUMENTED_BY"
    DEPENDS_ON = "DEPENDS_ON"


class IndexJobStatus(str, Enum):
    """Enum for indexing job status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
