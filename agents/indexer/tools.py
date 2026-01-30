"""Indexer agent tools for MCP server."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config.logging_config import get_logger
from config.settings import get_settings
from core.exceptions import IndexerError
from core.models import IndexingJob, IndexStatus
from core.types import IndexJobStatus
from database import get_neo4j_client
from utils.helpers import generate_correlation_id

from .parser import PythonASTParser
from .repository import RepositoryManager

logger = get_logger(__name__)


class IndexerTools:
    """MCP tools for the Indexer agent."""

    def __init__(self):
        """Initialize indexer tools."""
        self.settings = get_settings()
        self.repository_manager = RepositoryManager(
            repo_url=self.settings.fastapi_repo_url,
            clone_path=self.settings.repo_clone_path,
        )
        self.current_job: IndexingJob | None = None

    async def index_repository(self, force_reclone: bool = False) -> Dict[str, Any]:
        """Index the entire FastAPI repository.
        
        Args:
            force_reclone: If True, re-clone the repository.
            
        Returns:
            Dictionary with indexing job information.
        """
        job_id = f"idx_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{generate_correlation_id()[:8]}"
        
        self.current_job = IndexingJob(
            job_id=job_id,
            status=IndexJobStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
        
        logger.info(f"Starting repository indexing job: {job_id}")
        
        try:
            # Clone or update repository
            repo_path = await self.repository_manager.clone_repository(force=force_reclone)
            
            # Discover Python files
            python_files = self.repository_manager.discover_python_files()
            self.current_job.total_files = len(python_files)
            
            logger.info(f"Found {len(python_files)} Python files to index")
            
            # Get Neo4j client
            neo4j_client = await get_neo4j_client()
            
            # Index each file
            for i, file_path in enumerate(python_files):
                try:
                    await self.index_file(str(file_path))
                    self.current_job.files_processed = i + 1
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"Progress: {i + 1}/{len(python_files)} files indexed")
                        
                except Exception as e:
                    logger.error(f"Failed to index {file_path}: {e}")
                    # Continue with other files
            
            # Update job status
            self.current_job.status = IndexJobStatus.COMPLETED
            self.current_job.completed_at = datetime.utcnow()
            
            logger.info(
                f"Indexing job {job_id} completed: "
                f"{self.current_job.files_processed}/{self.current_job.total_files} files"
            )
            
            return {
                "success": True,
                "job_id": job_id,
                "files_processed": self.current_job.files_processed,
                "total_files": self.current_job.total_files,
            }
            
        except Exception as e:
            logger.error(f"Indexing job {job_id} failed: {e}")
            self.current_job.status = IndexJobStatus.FAILED
            self.current_job.error = str(e)
            self.current_job.completed_at = datetime.utcnow()
            
            raise IndexerError(f"Repository indexing failed: {e}")

    async def index_file(self, file_path: str) -> Dict[str, Any]:
        """Index a single Python file.
        
        Args:
            file_path: Path to Python file.
            
        Returns:
            Dictionary with indexing results.
        """
        try:
            file_path_obj = Path(file_path)
            
            # Get module path
            module_path = self.repository_manager.get_module_path(file_path_obj)
            
            # Parse file
            parser = PythonASTParser(file_path, module_path)
            entities, relationships = parser.parse_file()
            
            # Get Neo4j client
            neo4j_client = await get_neo4j_client()
            
            # Prepare batch write queries
            queries = []
            
            # Create nodes for entities
            for entity in entities:
                entity_dict = entity.to_dict()
                entity_type = entity_dict.pop("entity_type")
                name = entity_dict.pop("name")
                
                # Build properties string
                props = ", ".join(
                    f"{k}: ${k}" for k in entity_dict.keys()
                )
                
                query = (
                    f"MERGE (e:{entity_type} {{name: $name}}) "
                    f"SET e += {{{props}}}"
                )
                
                parameters = {"name": name, **entity_dict}
                queries.append((query, parameters))
            
            # Create relationships
            for rel in relationships:
                rel_dict = rel.to_dict()
                rel_type = rel_dict.pop("rel_type")
                source = rel_dict.pop("source")
                target = rel_dict.pop("target")
                
                query = (
                    f"MATCH (s {{name: $source}}), (t {{name: $target}}) "
                    f"MERGE (s)-[r:{rel_type}]->(t)"
                )
                
                parameters = {"source": source, "target": target, **rel_dict}
                queries.append((query, parameters))
            
            # Execute batch write
            if queries:
                await neo4j_client.execute_batch_write(queries)
            
            logger.debug(
                f"Indexed {file_path}: {len(entities)} entities, {len(relationships)} relationships"
            )
            
            return {
                "success": True,
                "file_path": file_path,
                "module_path": module_path,
                "entities_count": len(entities),
                "relationships_count": len(relationships),
            }
            
        except Exception as e:
            logger.error(f"Failed to index file {file_path}: {e}")
            raise IndexerError(f"File indexing failed: {e}")

    async def parse_python_ast(self, code: str, module_path: str = "temp") -> Dict[str, Any]:
        """Parse Python code and extract AST information.
        
        Args:
            code: Python source code.
            module_path: Module path for the code.
            
        Returns:
            Dictionary with extracted entities and relationships.
        """
        try:
            # Write code to temporary file
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                parser = PythonASTParser(temp_file, module_path)
                entities, relationships = parser.parse_file()
                
                return {
                    "success": True,
                    "entities": [e.to_dict() for e in entities],
                    "relationships": [r.to_dict() for r in relationships],
                }
            finally:
                # Clean up temp file
                Path(temp_file).unlink()
                
        except Exception as e:
            logger.error(f"Failed to parse AST: {e}")
            raise IndexerError(f"AST parsing failed: {e}")

    async def extract_entities(self, file_path: str) -> Dict[str, Any]:
        """Extract entities from a Python file without indexing.
        
        Args:
            file_path: Path to Python file.
            
        Returns:
            Dictionary with extracted entities.
        """
        try:
            file_path_obj = Path(file_path)
            module_path = self.repository_manager.get_module_path(file_path_obj)
            
            parser = PythonASTParser(file_path, module_path)
            entities, _ = parser.parse_file()
            
            return {
                "success": True,
                "file_path": file_path,
                "module_path": module_path,
                "entities": [e.to_dict() for e in entities],
            }
            
        except Exception as e:
            logger.error(f"Failed to extract entities from {file_path}: {e}")
            raise IndexerError(f"Entity extraction failed: {e}")

    async def get_index_status(self) -> IndexStatus:
        """Get current indexing status.
        
        Returns:
            IndexStatus object.
        """
        try:
            neo4j_client = await get_neo4j_client()
            
            # Count total entities and relationships
            total_entities = await neo4j_client.count_nodes()
            total_relationships = await neo4j_client.count_relationships()
            
            is_indexed = total_entities > 0
            
            return IndexStatus(
                is_indexed=is_indexed,
                last_indexed=self.current_job.completed_at if self.current_job else None,
                total_entities=total_entities,
                total_relationships=total_relationships,
                current_job=self.current_job if self.current_job and self.current_job.status == IndexJobStatus.IN_PROGRESS else None,
            )
            
        except Exception as e:
            logger.error(f"Failed to get index status: {e}")
            raise IndexerError(f"Failed to get index status: {e}")


# Global indexer tools instance
_indexer_tools: IndexerTools | None = None


def get_indexer_tools() -> IndexerTools:
    """Get or create global IndexerTools instance.
    
    Returns:
        IndexerTools instance.
    """
    global _indexer_tools
    
    if _indexer_tools is None:
        _indexer_tools = IndexerTools()
    
    return _indexer_tools
