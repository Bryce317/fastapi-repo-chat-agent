"""Repository management for cloning and file discovery."""

import os
import shutil
from pathlib import Path
from typing import List, Optional

from git import Repo
from git.exc import GitCommandError

from config.logging_config import get_logger
from core.exceptions import RepositoryError

logger = get_logger(__name__)


class RepositoryManager:
    """Manages FastAPI repository cloning and file operations."""

    def __init__(self, repo_url: str, clone_path: str):
        """Initialize repository manager.
        
        Args:
            repo_url: Git repository URL.
            clone_path: Local path to clone repository.
        """
        self.repo_url = repo_url
        self.clone_path = Path(clone_path)
        self.repo: Optional[Repo] = None

    async def clone_repository(self, force: bool = False) -> Path:
        """Clone the repository to local path.
        
        Args:
            force: If True, remove existing directory and re-clone.
            
        Returns:
            Path to cloned repository.
            
        Raises:
            RepositoryError: If cloning fails.
        """
        try:
            if self.clone_path.exists():
                if force:
                    logger.info(f"Removing existing repository at {self.clone_path}")
                    shutil.rmtree(self.clone_path)
                else:
                    logger.info(f"Repository already exists at {self.clone_path}")
                    self.repo = Repo(self.clone_path)
                    return self.clone_path
            
            # Create parent directory if it doesn't exist
            self.clone_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Cloning repository from {self.repo_url} to {self.clone_path}")
            self.repo = Repo.clone_from(
                self.repo_url,
                self.clone_path,
                depth=1,  # Shallow clone for faster cloning
            )
            
            logger.info(f"Repository cloned successfully to {self.clone_path}")
            return self.clone_path
            
        except GitCommandError as e:
            raise RepositoryError(f"Git command failed: {e}")
        except Exception as e:
            raise RepositoryError(f"Failed to clone repository: {e}")

    def discover_python_files(
        self, exclude_dirs: Optional[List[str]] = None
    ) -> List[Path]:
        """Discover all Python files in the repository.
        
        Args:
            exclude_dirs: List of directory names to exclude.
            
        Returns:
            List of Python file paths.
        """
        if not self.clone_path.exists():
            raise RepositoryError(f"Repository path does not exist: {self.clone_path}")
        
        exclude_dirs = exclude_dirs or [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "env",
            "node_modules",
            "tests",
            "test",
            "docs",
            "site",
            "build",
            "dist",
        ]
        
        python_files = []
        
        for root, dirs, files in os.walk(self.clone_path):
            # Remove excluded directories from dirs (in-place modification)
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    python_files.append(file_path)
        
        logger.info(f"Discovered {len(python_files)} Python files")
        return python_files

    def get_module_path(self, file_path: Path) -> str:
        """Convert file path to Python module path.
        
        Args:
            file_path: Absolute path to Python file.
            
        Returns:
            Module path (e.g., 'fastapi.routing.router').
        """
        # Get relative path from repository root
        try:
            relative_path = file_path.relative_to(self.clone_path)
        except ValueError:
            raise RepositoryError(f"File {file_path} is not in repository")
        
        # Convert path to module notation
        parts = list(relative_path.parts)
        
        # Remove .py extension from last part
        if parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]
        
        # Remove __init__ if present
        if parts[-1] == '__init__':
            parts = parts[:-1]
        
        # Join with dots
        module_path = '.'.join(parts)
        
        return module_path

    def get_repository_info(self) -> dict:
        """Get information about the cloned repository.
        
        Returns:
            Dictionary with repository information.
        """
        if not self.repo:
            raise RepositoryError("Repository not initialized")
        
        return {
            "url": self.repo_url,
            "path": str(self.clone_path),
            "branch": self.repo.active_branch.name if self.repo.head.is_valid() else "N/A",
            "commit": str(self.repo.head.commit) if self.repo.head.is_valid() else "N/A",
            "remote_url": self.repo.remotes.origin.url if self.repo.remotes else "N/A",
        }

    def update_repository(self) -> bool:
        """Pull latest changes from remote repository.
        
        Returns:
            True if updates were pulled, False if already up to date.
            
        Raises:
            RepositoryError: If update fails.
        """
        if not self.repo:
            raise RepositoryError("Repository not initialized")
        
        try:
            origin = self.repo.remotes.origin
            fetch_info = origin.pull()
            
            if fetch_info:
                logger.info(f"Repository updated: {len(fetch_info)} changes")
                return True
            else:
                logger.info("Repository already up to date")
                return False
                
        except GitCommandError as e:
            raise RepositoryError(f"Failed to update repository: {e}")

    def cleanup(self) -> None:
        """Remove cloned repository."""
        if self.clone_path.exists():
            logger.info(f"Removing repository at {self.clone_path}")
            shutil.rmtree(self.clone_path)
