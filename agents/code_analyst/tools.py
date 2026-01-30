"""Code Analyst agent tools for MCP server."""

from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from config.logging_config import get_logger
from config.settings import get_settings
from core.exceptions import CodeAnalystError, OpenAIError
from database import get_neo4j_client
from utils.helpers import async_retry

from .analyzer import CodeAnalyzer
from .patterns import PatternDetector

logger = get_logger(__name__)


class CodeAnalystTools:
    """MCP tools for the Code Analyst agent."""

    def __init__(self):
        """Initialize code analyst tools."""
        self.settings = get_settings()
        self.analyzer = CodeAnalyzer()
        self.pattern_detector = PatternDetector()
        self.openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def analyze_function(self, function_name: str) -> Dict[str, Any]:
        """Perform deep analysis of a function.
        
        Args:
            function_name: Fully qualified function name.
            
        Returns:
            Dictionary with function analysis.
        """
        try:
            # Get function code from Neo4j
            neo4j_client = await get_neo4j_client()
            
            query = """
                MATCH (f)
                WHERE f.name = $name AND (f:Function OR f:Method)
                RETURN f
            """
            
            result = await neo4j_client.execute_read(query, {"name": function_name})
            
            if not result:
                return {"error": f"Function '{function_name}' not found"}
            
            function_data = result[0]['f']
            
            # Perform complexity analysis
            # Note: We'd need the actual code, which isn't stored in our schema
            # For now, return metadata analysis
            
            analysis = {
                "success": True,
                "function_name": function_name,
                "signature": function_data.get("signature", "N/A"),
                "is_async": function_data.get("is_async", False),
                "docstring": function_data.get("docstring", ""),
                "line_number": function_data.get("line_number", 0),
                "module_path": function_data.get("module_path", ""),
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Function analysis failed: {e}")
            raise CodeAnalystError(f"Failed to analyze function: {e}")

    async def analyze_class(self, class_name: str) -> Dict[str, Any]:
        """Perform comprehensive class analysis.
        
        Args:
            class_name: Fully qualified class name.
            
        Returns:
            Dictionary with class analysis.
        """
        try:
            neo4j_client = await get_neo4j_client()
            
            # Get class and its members
            query = """
                MATCH (c:Class {name: $name})
                OPTIONAL MATCH (c)-[:CONTAINS]->(method)
                OPTIONAL MATCH (c)-[:INHERITS_FROM]->(parent)
                RETURN c, collect(DISTINCT method) as methods, collect(DISTINCT parent) as parents
            """
            
            result = await neo4j_client.execute_read(query, {"name": class_name})
            
            if not result:
                return {"error": f"Class '{class_name}' not found"}
            
            record = result[0]
            class_data = record['c']
            methods = record['methods']
            parents = record['parents']
            
            analysis = {
                "success": True,
                "class_name": class_name,
                "docstring": class_data.get("docstring", ""),
                "is_abstract": class_data.get("is_abstract", False),
                "parent_classes": [p.get('name', 'Unknown') for p in parents if p],
                "method_count": len([m for m in methods if m]),
                "methods": [
                    {
                        "name": m.get('name', 'Unknown'),
                        "is_async": m.get('is_async', False),
                        "is_static": m.get('is_static', False),
                    }
                    for m in methods if m
                ],
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Class analysis failed: {e}")
            raise CodeAnalystError(f"Failed to analyze class: {e}")

    async def find_patterns(self, entity_name: str) -> Dict[str, Any]:
        """Detect design patterns in code entity.
        
        Args:
            entity_name: Name of the entity to analyze.
            
        Returns:
            Dictionary with detected patterns.
        """
        try:
            # This is a simplified version - in production, we'd retrieve actual code
            patterns = {
                "success": True,
                "entity": entity_name,
                "patterns": [],
                "note": "Pattern detection requires source code retrieval",
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            raise CodeAnalystError(f"Failed to detect patterns: {e}")

    async def get_code_snippet(
        self, 
        entity_name: str, 
        context_lines: int = 5
    ) -> Dict[str, Any]:
        """Extract code snippet with surrounding context.
        
        Args:
            entity_name: Name of the entity.
            context_lines: Number of lines of context to include.
            
        Returns:
            Dictionary with code snippet.
        """
        try:
            neo4j_client = await get_neo4j_client()
            
            query = """
                MATCH (e {name: $name})
                RETURN e, labels(e) as entity_type
            """
            
            result = await neo4j_client.execute_read(query, {"name": entity_name})
            
            if not result:
                return {"error": f"Entity '{entity_name}' not found"}
            
            entity = result[0]['e']
            
            snippet = {
                "success": True,
                "entity_name": entity_name,
                "entity_type": result[0].get('entity_type', ['Unknown'])[0],
                "line_number": entity.get("line_number", 0),
                "signature": entity.get("signature", "N/A"),
                "docstring": entity.get("docstring", ""),
                "note": "Full source code retrieval not implemented in current schema",
            }
            
            return snippet
            
        except Exception as e:
            logger.error(f"Code snippet extraction failed: {e}")
            raise CodeAnalystError(f"Failed to get code snippet: {e}")

    @async_retry(max_retries=2, delay=1.0)
    async def explain_implementation(self, entity_name: str) -> Dict[str, Any]:
        """Generate LLM explanation of how code works.
        
        Args:
            entity_name: Name of the entity to explain.
            
        Returns:
            Dictionary with explanation.
        """
        try:
            # Get entity information
            snippet = await self.get_code_snippet(entity_name)
            
            if not snippet.get("success"):
                return snippet
            
            # Build prompt for LLM
            prompt = f"""Explain how the following FastAPI code entity works:

Entity: {entity_name}
Type: {snippet.get('entity_type', 'Unknown')}
Signature: {snippet.get('signature', 'N/A')}

Docstring:
{snippet.get('docstring', 'No docstring available')}

Please provide a clear, concise explanation of what this code does and how it works.
"""
            
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in Python and FastAPI. Explain code clearly and concisely.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.settings.openai_temperature,
                max_tokens=self.settings.openai_max_tokens,
            )
            
            explanation = response.choices[0].message.content
            
            return {
                "success": True,
                "entity_name": entity_name,
                "explanation": explanation,
            }
            
        except Exception as e:
            logger.error(f"Implementation explanation failed: {e}")
            raise CodeAnalystError(f"Failed to explain implementation: {e}")

    async def compare_implementations(
        self, 
        entity1: str, 
        entity2: str
    ) -> Dict[str, Any]:
        """Compare two code entities.
        
        Args:
            entity1: First entity name.
            entity2: Second entity name.
            
        Returns:
            Dictionary with comparison.
        """
        try:
            # Get both entities
            snippet1 = await self.get_code_snippet(entity1)
            snippet2 = await self.get_code_snippet(entity2)
            
            if not snippet1.get("success") or not snippet2.get("success"):
                return {"error": "One or both entities not found"}
            
            comparison = {
                "success": True,
                "entity1": {
                    "name": entity1,
                    "type": snippet1.get("entity_type"),
                    "signature": snippet1.get("signature"),
                },
                "entity2": {
                    "name": entity2,
                    "type": snippet2.get("entity_type"),
                    "signature": snippet2.get("signature"),
                },
                "comparison": f"Comparing {entity1} and {entity2}",
                "note": "Full comparison requires source code analysis",
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Implementation comparison failed: {e}")
            raise CodeAnalystError(f"Failed to compare implementations: {e}")


# Global code analyst tools instance
_code_analyst_tools: CodeAnalystTools | None = None


def get_code_analyst_tools() -> CodeAnalystTools:
    """Get or create global CodeAnalystTools instance.
    
    Returns:
        CodeAnalystTools instance.
    """
    global _code_analyst_tools
    
    if _code_analyst_tools is None:
        _code_analyst_tools = CodeAnalystTools()
    
    return _code_analyst_tools
