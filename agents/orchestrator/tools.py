"""Orchestrator agent tools for query analysis and response synthesis."""

import time
from typing import Any, Dict, List

from openai import AsyncOpenAI

from config.logging_config import get_logger
from config.settings import get_settings
from core.exceptions import OrchestratorError
from core.models import AgentResponse, QueryIntent
from core.types import AgentType, QueryType
from utils.helpers import async_retry

logger = get_logger(__name__)


class OrchestratorTools:
    """Tools for the Orchestrator agent."""

    def __init__(self):
        """Initialize orchestrator tools."""
        self.settings = get_settings()
        self.openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    @async_retry(max_retries=2, delay=1.0)
    async def analyze_query(
        self, 
        query: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> QueryIntent:
        """Analyze user query to determine intent and extract entities.
        
        Args:
            query: User query string.
            conversation_history: Previous conversation messages.
            
        Returns:
            QueryIntent object with classification and entities.
        """
        conversation_history = conversation_history or []
        
        try:
            # Build prompt for query analysis
            prompt = f"""Analyze the following user query about the FastAPI codebase and provide:
1. Query type (simple/medium/complex)
2. Extracted entities (class names, function names, module names, concepts)
3. High-level intent
4. Whether code analysis is needed
5. Whether graph query is needed

Query: "{query}"

Respond in JSON format:
{{
    "query_type": "simple|medium|complex",
    "entities": ["Entity1", "Entity2", ...],
    "intent": "brief description",
    "requires_code_analysis": true|false,
    "requires_graph_query": true|false
}}
"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing queries about code repositories. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temperature for more consistent JSON
                max_tokens=500,
            )
            
            # Parse JSON response
            import json
            content = response.choices[0].message.content
            
            # Extract JSON from response (handle code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            analysis = json.loads(content.strip())
            
            # Create QueryIntent
            query_intent = QueryIntent(
                query_type=QueryType(analysis.get("query_type", "simple")),
                entities=analysis.get("entities", []),
                intent=analysis.get("intent", ""),
                requires_code_analysis=analysis.get("requires_code_analysis", False),
                requires_graph_query=analysis.get("requires_graph_query", False),
            )
            
            logger.info(
                f"Query analyzed: type={query_intent.query_type}, "
                f"entities={len(query_intent.entities)}"
            )
            
            return query_intent
            
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            # Fallback to simple classification
            return QueryIntent(
                query_type=QueryType.SIMPLE,
                entities=[],
                intent=query,
                requires_code_analysis=True,
                requires_graph_query=True,
            )

    def route_to_agents(self, query_intent: QueryIntent) -> List[AgentType]:
        """Determine which agents should handle the query.
        
        Args:
            query_intent: Analyzed query intent.
            
        Returns:
            List of agent types to invoke.
        """
        agents = []
        
        # Always use graph query for entity lookups
        if query_intent.requires_graph_query or query_intent.entities:
            agents.append(AgentType.GRAPH_QUERY)
        
        # Use code analyst for deep analysis
        if query_intent.requires_code_analysis:
            agents.append(AgentType.CODE_ANALYST)
        
        # For complex queries, use all available agents
        if query_intent.query_type == QueryType.COMPLEX:
            if AgentType.GRAPH_QUERY not in agents:
                agents.append(AgentType.GRAPH_QUERY)
            if AgentType.CODE_ANALYST not in agents:
                agents.append(AgentType.CODE_ANALYST)
        
        # If no agents selected, default to graph query
        if not agents:
            agents.append(AgentType.GRAPH_QUERY)
        
        logger.info(f"Routing to agents: {[a.value for a in agents]}")
        
        return agents

    @async_retry(max_retries=2, delay=1.0)
    async def synthesize_response(
        self,
        query: str,
        agent_responses: List[AgentResponse],
        conversation_history: List[Dict[str, str]] = None,
    ) -> str:
        """Synthesize final response from multiple agent outputs.
        
        Args:
            query: Original user query.
            agent_responses: List of agent responses.
            conversation_history: Previous conversation messages.
            
        Returns:
            Synthesized response string.
        """
        conversation_history = conversation_history or []
        
        try:
            # Build context from agent responses
            agent_outputs = []
            for resp in agent_responses:
                if resp.success:
                    agent_outputs.append(
                        f"[{resp.agent_type.value.upper()}]: {resp.content}"
                    )
            
            if not agent_outputs:
                return "I couldn't find relevant information to answer your question."
            
            # Build synthesis prompt
            context = "\n\n".join(agent_outputs)
            
            prompt = f"""Based on the following information from different analysis agents, provide a comprehensive answer to the user's question.

User Question: "{query}"

Agent Outputs:
{context}

Synthesize these outputs into a clear, coherent response. Be specific and cite code entities when relevant.
"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.settings.synthesis_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful FastAPI code assistant. Provide clear, accurate answers based on the analysis results provided.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.settings.openai_temperature,
                max_tokens=self.settings.openai_max_tokens,
            )
            
            synthesized = response.choices[0].message.content
            
            logger.info(f"Response synthesized ({len(synthesized)} chars)")
            
            return synthesized
            
        except Exception as e:
            logger.error(f"Response synthesis failed: {e}")
            raise OrchestratorError(f"Failed to synthesize response: {e}")


# Global orchestrator tools instance
_orchestrator_tools: OrchestratorTools | None = None


def get_orchestrator_tools() -> OrchestratorTools:
    """Get or create global OrchestratorTools instance.
    
    Returns:
        OrchestratorTools instance.
    """
    global _orchestrator_tools
    
    if _orchestrator_tools is None:
        _orchestrator_tools = OrchestratorTools()
    
    return _orchestrator_tools
