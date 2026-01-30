"""LangGraph state definition for orchestrator workflow."""

from typing import Any, Dict, List, Optional, TypedDict

from core.models import AgentResponse, QueryIntent
from core.types import AgentType


class AgentState(TypedDict, total=False):
    """State passed through the LangGraph workflow."""
    
    # Input
    query: str
    session_id: str
    conversation_history: List[Dict[str, str]]
    
    # Query analysis
    query_intent: Optional[QueryIntent]
    entities: List[str]
    
    # Agent routing
    agents_to_invoke: List[AgentType]
    
    # Agent responses
    indexer_response: Optional[AgentResponse]
    graph_query_response: Optional[AgentResponse]
    code_analyst_response: Optional[AgentResponse]
    
    # Final synthesis
    synthesized_response: Optional[str]
    processing_time: float
    
    # Error handling
    error: Optional[str]
