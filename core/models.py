"""Pydantic models for API requests, responses, and internal data structures."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .types import AgentType, IndexJobStatus, QueryType


class Message(BaseModel):
    """Represents a single message in a conversation."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "What is the FastAPI class?",
                "timestamp": "2024-01-29T12:00:00Z",
            }
        }


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., min_length=1, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    stream: bool = Field(default=False, description="Whether to stream the response")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "How does FastAPI handle request validation?",
                "session_id": "abc123",
                "stream": False,
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str = Field(..., description="Assistant's response")
    session_id: str = Field(..., description="Session ID")
    agents_used: List[AgentType] = Field(
        default_factory=list, description="List of agents that contributed to this response"
    )
    processing_time: float = Field(..., description="Processing time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "FastAPI uses Pydantic models for request validation...",
                "session_id": "abc123",
                "agents_used": ["orchestrator", "graph_query", "code_analyst"],
                "processing_time": 2.5,
            }
        }


class QueryIntent(BaseModel):
    """Parsed intent from user query."""

    query_type: QueryType = Field(..., description="Classification of query complexity")
    entities: List[str] = Field(
        default_factory=list, description="Extracted entities (class names, function names, etc.)"
    )
    intent: str = Field(..., description="High-level intent description")
    requires_code_analysis: bool = Field(
        default=False, description="Whether deep code analysis is needed"
    )
    requires_graph_query: bool = Field(
        default=False, description="Whether graph traversal is needed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query_type": "medium",
                "entities": ["FastAPI", "Request", "validation"],
                "intent": "Understand request validation mechanism",
                "requires_code_analysis": True,
                "requires_graph_query": True,
            }
        }


class AgentResponse(BaseModel):
    """Response from an individual agent."""

    agent_type: AgentType = Field(..., description="Type of agent that generated this response")
    content: str = Field(..., description="Response content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata from the agent"
    )
    processing_time: float = Field(..., description="Agent processing time in seconds")
    success: bool = Field(default=True, description="Whether the agent succeeded")
    error: Optional[str] = Field(None, description="Error message if agent failed")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_type": "graph_query",
                "content": "Found 12 classes that inherit from APIRouter",
                "metadata": {"entity_count": 12},
                "processing_time": 0.8,
                "success": True,
            }
        }


class IndexingJob(BaseModel):
    """Represents an indexing job."""

    job_id: str = Field(..., description="Unique job identifier")
    status: IndexJobStatus = Field(..., description="Current job status")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    files_processed: int = Field(default=0, description="Number of files processed")
    total_files: int = Field(default=0, description="Total number of files to process")
    error: Optional[str] = Field(None, description="Error message if job failed")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "idx_20240129_120000",
                "status": "in_progress",
                "started_at": "2024-01-29T12:00:00Z",
                "files_processed": 45,
                "total_files": 120,
            }
        }


class IndexStatus(BaseModel):
    """Current status of repository indexing."""

    is_indexed: bool = Field(..., description="Whether repository is indexed")
    last_indexed: Optional[datetime] = Field(None, description="Last indexing timestamp")
    total_entities: int = Field(default=0, description="Total entities in graph")
    total_relationships: int = Field(default=0, description="Total relationships in graph")
    current_job: Optional[IndexingJob] = Field(None, description="Currently running job")


class GraphStatistics(BaseModel):
    """Statistics about the knowledge graph."""

    total_nodes: int = Field(..., description="Total number of nodes")
    total_relationships: int = Field(..., description="Total number of relationships")
    nodes_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Node counts by type"
    )
    relationships_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Relationship counts by type"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_nodes": 1542,
                "total_relationships": 3821,
                "nodes_by_type": {
                    "Module": 95,
                    "Class": 234,
                    "Function": 876,
                    "Method": 337,
                },
                "relationships_by_type": {
                    "CONTAINS": 1203,
                    "IMPORTS": 456,
                    "CALLS": 1842,
                    "INHERITS_FROM": 320,
                },
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response for agents."""

    status: str = Field(..., description="Overall health status")
    agents: Dict[str, bool] = Field(
        default_factory=dict, description="Health status of each agent"
    )
    neo4j_connected: bool = Field(..., description="Neo4j connection status")
    openai_available: bool = Field(..., description="OpenAI API availability")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "agents": {
                    "orchestrator": True,
                    "indexer": True,
                    "graph_query": True,
                    "code_analyst": True,
                },
                "neo4j_connected": True,
                "openai_available": True,
            }
        }
