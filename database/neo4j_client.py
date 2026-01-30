"""Neo4j client for graph database operations."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import ServiceUnavailable

from config.logging_config import get_logger
from config.settings import get_settings
from core.exceptions import Neo4jConnectionError

logger = get_logger(__name__)


class Neo4jClient:
    """Async Neo4j client with connection pooling and transaction management."""

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """Initialize Neo4j client.
        
        Args:
            uri: Neo4j connection URI (bolt://host:port).
            user: Neo4j username.
            password: Neo4j password.
            database: Database name (default: neo4j).
        """
        self.uri = uri
        self.user = user
        self.database = database
        self._driver = None
        
        try:
            self._driver = AsyncGraphDatabase.driver(
                uri, auth=(user, password), max_connection_pool_size=50
            )
            logger.info(f"Neo4j driver initialized for {uri}")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")
            raise Neo4jConnectionError(f"Failed to initialize Neo4j driver: {e}")

    async def verify_connectivity(self) -> bool:
        """Verify connection to Neo4j database.
        
        Returns:
            True if connection is successful.
            
        Raises:
            Neo4jConnectionError: If connection fails.
        """
        if not self._driver:
            raise Neo4jConnectionError("Driver not initialized")
        
        try:
            await self._driver.verify_connectivity()
            logger.info("Neo4j connectivity verified")
            return True
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise Neo4jConnectionError(f"Neo4j service unavailable: {e}")
        except Exception as e:
            logger.error(f"Failed to verify Neo4j connectivity: {e}")
            raise Neo4jConnectionError(f"Failed to verify connectivity: {e}")

    async def close(self) -> None:
        """Close the Neo4j driver and release resources."""
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j driver closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Create a Neo4j session context manager.
        
        Yields:
            AsyncSession for executing queries.
        """
        if not self._driver:
            raise Neo4jConnectionError("Driver not initialized")
        
        async with self._driver.session(database=self.database) as session:
            yield session

    async def execute_read(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read query and return results.
        
        Args:
            query: Cypher query string.
            parameters: Query parameters.
            
        Returns:
            List of result records as dictionaries.
        """
        parameters = parameters or {}
        
        try:
            async with self.session() as session:
                result = await session.run(query, parameters)
                records = await result.data()
                logger.debug(f"Read query executed: {len(records)} records returned")
                return records
        except Exception as e:
            logger.error(f"Read query failed: {e}")
            raise Neo4jConnectionError(f"Read query failed: {e}")

    async def execute_write(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a write query and return results.
        
        Args:
            query: Cypher query string.
            parameters: Query parameters.
            
        Returns:
            List of result records as dictionaries.
        """
        parameters = parameters or {}
        
        try:
            async with self.session() as session:
                result = await session.run(query, parameters)
                records = await result.data()
                logger.debug(f"Write query executed: {len(records)} records affected")
                return records
        except Exception as e:
            logger.error(f"Write query failed: {e}")
            raise Neo4jConnectionError(f"Write query failed: {e}")

    async def execute_batch_write(
        self, queries: List[tuple[str, Dict[str, Any]]]
    ) -> int:
        """Execute multiple write queries in a single transaction.
        
        Args:
            queries: List of (query, parameters) tuples.
            
        Returns:
            Number of queries executed.
        """
        try:
            async with self.session() as session:
                async with session.begin_transaction() as tx:
                    for query, parameters in queries:
                        await tx.run(query, parameters)
                    await tx.commit()
                
                logger.debug(f"Batch write executed: {len(queries)} queries")
                return len(queries)
        except Exception as e:
            logger.error(f"Batch write failed: {e}")
            raise Neo4jConnectionError(f"Batch write failed: {e}")

    async def count_nodes(self, label: Optional[str] = None) -> int:
        """Count nodes in the graph.
        
        Args:
            label: Optional node label to filter by.
            
        Returns:
            Number of nodes.
        """
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
        else:
            query = "MATCH (n) RETURN count(n) as count"
        
        result = await self.execute_read(query)
        return result[0]["count"] if result else 0

    async def count_relationships(self, rel_type: Optional[str] = None) -> int:
        """Count relationships in the graph.
        
        Args:
            rel_type: Optional relationship type to filter by.
            
        Returns:
            Number of relationships.
        """
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
        else:
            query = "MATCH ()-[r]->() RETURN count(r) as count"
        
        result = await self.execute_read(query)
        return result[0]["count"] if result else 0


# Global client instance
_neo4j_client: Optional[Neo4jClient] = None


async def get_neo4j_client() -> Neo4jClient:
    """Get or create the global Neo4j client instance.
    
    Returns:
        Neo4jClient instance.
    """
    global _neo4j_client
    
    if _neo4j_client is None:
        settings = get_settings()
        _neo4j_client = Neo4jClient(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        await _neo4j_client.verify_connectivity()
    
    return _neo4j_client


async def close_neo4j_client() -> None:
    """Close the global Neo4j client."""
    global _neo4j_client
    
    if _neo4j_client:
        await _neo4j_client.close()
        _neo4j_client = None
