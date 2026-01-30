"""LangGraph workflow for orchestrating multi-agent interactions."""

import time
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from config.logging_config import get_logger
from core.models import AgentResponse
from core.types import AgentType
from memory import get_conversation_memory

from ..code_analyst.tools import get_code_analyst_tools
from ..graph_query.tools import get_graph_query_tools
from .state import AgentState
from .tools import get_orchestrator_tools

logger = get_logger(__name__)


class OrchestratorGraph:
    """LangGraph workflow for coordinating agent interactions."""

    def __init__(self):
        """Initialize orchestrator graph."""
        self.orchestrator_tools = get_orchestrator_tools()
        self.graph_query_tools = get_graph_query_tools()
        self.code_analyst_tools = get_code_analyst_tools()
        self.conversation_memory = get_conversation_memory()
        
        # Build the graph
        self.workflow = self._build_graph()
        self.app = self.workflow.compile()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.
        
        Returns:
            StateGraph instance.
        """
        # Create graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_query", self._analyze_query_node)
        workflow.add_node("route_agents", self._route_agents_node)
        workflow.add_node("call_graph_query", self._call_graph_query_node)
        workflow.add_node("call_code_analyst", self._call_code_analyst_node)
        workflow.add_node("synthesize", self._synthesize_node)
        
        # Add edges
        workflow.set_entry_point("analyze_query")
        workflow.add_edge("analyze_query", "route_agents")
        
        # Conditional routing from route_agents
        workflow.add_conditional_edges(
            "route_agents",
            self._should_call_agents,
            {
                "graph_query": "call_graph_query",
                "code_analyst": "call_code_analyst",
                "both": "call_graph_query",  # Call graph_query first
                "synthesize": "synthesize",
            },
        )
        
        # After graph_query, check if we need code_analyst
        workflow.add_conditional_edges(
            "call_graph_query",
            self._after_graph_query,
            {
                "code_analyst": "call_code_analyst",
                "synthesize": "synthesize",
            },
        )
        
        # After code_analyst, always synthesize
        workflow.add_edge("call_code_analyst", "synthesize")
        
        # End after synthesis
        workflow.add_edge("synthesize", END)
        
        return workflow

    async def _analyze_query_node(self, state: AgentState) -> Dict[str, Any]:
        """Analyze the user query.
        
        Args:
            state: Current state.
            
        Returns:
            Updated state with query intent.
        """
        logger.info(f"Analyzing query: {state['query'][:50]}...")
        
        query_intent = await self.orchestrator_tools.analyze_query(
            state["query"],
            state.get("conversation_history", []),
        )
        
        return {
            "query_intent": query_intent,
            "entities": query_intent.entities,
        }

    async def _route_agents_node(self, state: AgentState) -> Dict[str, Any]:
        """Determine which agents to invoke.
        
        Args:
            state: Current state.
            
        Returns:
            Updated state with agents to invoke.
        """
        query_intent = state["query_intent"]
        
        agents_to_invoke = self.orchestrator_tools.route_to_agents(query_intent)
        
        logger.info(f"Routing to {len(agents_to_invoke)} agents")
        
        return {"agents_to_invoke": agents_to_invoke}

    def _should_call_agents(self, state: AgentState) -> str:
        """Conditional edge function to determine which agents to call.
        
        Args:
            state: Current state.
            
        Returns:
            Next node to visit.
        """
        agents = state.get("agents_to_invoke", [])
        
        if not agents:
            return "synthesize"
        
        has_graph_query = AgentType.GRAPH_QUERY in agents
        has_code_analyst = AgentType.CODE_ANALYST in agents
        
        if has_graph_query and has_code_analyst:
            return "both"
        elif has_graph_query:
            return "graph_query"
        elif has_code_analyst:
            return "code_analyst"
        else:
            return "synthesize"

    async def _call_graph_query_node(self, state: AgentState) -> Dict[str, Any]:
        """Call the Graph Query agent.
        
        Args:
            state: Current state.
            
        Returns:
            Updated state with graph query response.
        """
        logger.info("Calling Graph Query agent")
        
        start_time = time.time()
        
        try:
            # Determine what to query based on entities
            entities = state.get("entities", [])
            query_results = []
            
            if entities:
                # Search for each entity
                for entity in entities[:3]:  # Limit to first 3 entities
                    result = await self.graph_query_tools.find_entity(entity)
                    if result.get("success"):
                        query_results.append(f"Found {result.get('count', 0)} entities matching '{entity}'")
            else:
                # General search based on query
                query_results.append("Performed general repository search")
            
            content = " ".join(query_results) if query_results else "No results found"
            
            response = AgentResponse(
                agent_type=AgentType.GRAPH_QUERY,
                content=content,
                metadata={"entities_searched": entities},
                processing_time=time.time() - start_time,
                success=True,
            )
            
        except Exception as e:
            logger.error(f"Graph Query agent failed: {e}")
            response = AgentResponse(
                agent_type=AgentType.GRAPH_QUERY,
                content="",
                metadata={},
                processing_time=time.time() - start_time,
                success=False,
                error=str(e),
            )
        
        return {"graph_query_response": response}

    def _after_graph_query(self, state: AgentState) -> str:
        """Determine next step after graph query.
        
        Args:
            state: Current state.
            
        Returns:
            Next node to visit.
        """
        agents = state.get("agents_to_invoke", [])
        
        if AgentType.CODE_ANALYST in agents:
            return "code_analyst"
        else:
            return "synthesize"

    async def _call_code_analyst_node(self, state: AgentState) -> Dict[str, Any]:
        """Call the Code Analyst agent.
        
        Args:
            state: Current state.
            
        Returns:
            Updated state with code analyst response.
        """
        logger.info("Calling Code Analyst agent")
        
        start_time = time.time()
        
        try:
            # Use entities from query analysis
            entities = state.get("entities", [])
            analysis_results = []
            
            if entities:
                # Analyze first entity
                entity = entities[0]
                result = await self.code_analyst_tools.explain_implementation(entity)
                if result.get("success"):
                    analysis_results.append(result.get("explanation", ""))
            
            content = " ".join(analysis_results) if analysis_results else "Code analysis completed"
            
            response = AgentResponse(
                agent_type=AgentType.CODE_ANALYST,
                content=content,
                metadata={"entities_analyzed": entities},
                processing_time=time.time() - start_time,
                success=True,
            )
            
        except Exception as e:
            logger.error(f"Code Analyst agent failed: {e}")
            response = AgentResponse(
                agent_type=AgentType.CODE_ANALYST,
                content="",
                metadata={},
                processing_time=time.time() - start_time,
                success=False,
                error=str(e),
            )
        
        return {"code_analyst_response": response}

    async def _synthesize_node(self, state: AgentState) -> Dict[str, Any]:
        """Synthesize final response from agent outputs.
        
        Args:
            state: Current state.
            
        Returns:
            Updated state with synthesized response.
        """
        logger.info("Synthesizing final response")
        
        # Collect agent responses
        agent_responses = []
        
        for key in ["graph_query_response", "code_analyst_response"]:
            if key in state and state[key]:
                agent_responses.append(state[key])
        
        # Synthesize response
        synthesized = await self.orchestrator_tools.synthesize_response(
            state["query"],
            agent_responses,
            state.get("conversation_history", []),
        )
        
        return {"synthesized_response": synthesized}

    async def process_query(
        self, 
        query: str, 
        session_id: str,
        conversation_history: list = None
    ) -> Dict[str, Any]:
        """Process a user query through the orchestrator workflow.
        
        Args:
            query: User query.
            session_id: Session identifier.
            conversation_history: Previous conversation messages.
            
        Returns:
            Dictionary with final response and metadata.
        """
        start_time = time.time()
        
        # Initialize state
        initial_state: AgentState = {
            "query": query,
            "session_id": session_id,
            "conversation_history": conversation_history or [],
        }
        
        try:
            # Run the graph
            final_state = await self.app.ainvoke(initial_state)
            
            processing_time = time.time() - start_time
            
            # Collect which agents were used
            agents_used = []
            if final_state.get("graph_query_response"):
                agents_used.append(AgentType.GRAPH_QUERY)
            if final_state.get("code_analyst_response"):
                agents_used.append(AgentType.CODE_ANALYST)
            
            result = {
                "success": True,
                "response": final_state.get("synthesized_response", "No response generated"),
                "agents_used": agents_used,
                "processing_time": processing_time,
                "session_id": session_id,
            }
            
            # Store in conversation memory
            self.conversation_memory.add_user_message(session_id, query)
            self.conversation_memory.add_assistant_message(
                session_id, result["response"]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Orchestrator workflow failed: {e}")
            return {
                "success": False,
                "response": f"I encountered an error processing your query: {str(e)}",
                "agents_used": [],
                "processing_time": time.time() - start_time,
                "session_id": session_id,
                "error": str(e),
            }


# Global orchestrator graph instance
_orchestrator_graph: OrchestratorGraph | None = None


def get_orchestrator_graph() -> OrchestratorGraph:
    """Get or create global OrchestratorGraph instance.
    
    Returns:
        OrchestratorGraph instance.
    """
    global _orchestrator_graph
    
    if _orchestrator_graph is None:
        _orchestrator_graph = OrchestratorGraph()
    
    return _orchestrator_graph
