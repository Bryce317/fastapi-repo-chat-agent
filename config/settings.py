"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    openai_max_tokens: int = Field(default=2000, gt=0)

    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(..., description="Neo4j password")
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")

    # Application Configuration
    environment: Literal["development", "testing", "production"] = Field(
        default="development", description="Application environment"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, gt=0, lt=65536)

    # Repository Configuration
    fastapi_repo_url: str = Field(
        default="https://github.com/tiangolo/fastapi.git",
        description="FastAPI repository URL",
    )
    repo_clone_path: str = Field(
        default="./data/repositories/fastapi",
        description="Path to clone repository",
    )
    index_on_startup: bool = Field(
        default=False, description="Whether to index repository on startup"
    )

    # Agent Configuration
    agent_timeout: int = Field(default=30, gt=0, description="Agent timeout in seconds")
    agent_max_retries: int = Field(default=3, ge=0, description="Maximum agent retries")
    agent_retry_delay: int = Field(
        default=1, ge=0, description="Delay between retries in seconds"
    )

    # Memory Configuration
    max_conversation_history: int = Field(
        default=20, gt=0, description="Maximum messages to keep in conversation history"
    )
    response_cache_ttl: int = Field(
        default=3600, gt=0, description="Response cache TTL in seconds"
    )

    # Orchestrator Configuration
    max_parallel_agents: int = Field(
        default=3, gt=0, description="Maximum number of agents to run in parallel"
    )
    synthesis_model: str = Field(
        default="gpt-4o-mini", description="Model for response synthesis"
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings instance loaded from environment variables.
    """
    return Settings()
