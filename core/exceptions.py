"""Custom exception hierarchy for the multi-agent system."""


class AgentException(Exception):
    """Base exception for all agent-related errors."""

    def __init__(self, message: str, agent_type: str = "Unknown"):
        self.agent_type = agent_type
        self.message = message
        super().__init__(f"[{agent_type}] {message}")


class OrchestratorError(AgentException):
    """Exception raised by the Orchestrator agent."""

    def __init__(self, message: str):
        super().__init__(message, agent_type="Orchestrator")


class IndexerError(AgentException):
    """Exception raised by the Indexer agent."""

    def __init__(self, message: str):
        super().__init__(message, agent_type="Indexer")


class GraphQueryError(AgentException):
    """Exception raised by the Graph Query agent."""

    def __init__(self, message: str):
        super().__init__(message, agent_type="GraphQuery")


class CodeAnalystError(AgentException):
    """Exception raised by the Code Analyst agent."""

    def __init__(self, message: str):
        super().__init__(message, agent_type="CodeAnalyst")


class Neo4jConnectionError(Exception):
    """Exception raised when Neo4j connection fails."""

    def __init__(self, message: str = "Failed to connect to Neo4j database"):
        self.message = message
        super().__init__(self.message)


class OpenAIError(Exception):
    """Exception raised when OpenAI API calls fail."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(
            f"{message}" + (f" (status: {status_code})" if status_code else "")
        )


class ValidationError(Exception):
    """Exception raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        self.message = message
        super().__init__(f"{message}" + (f" (field: {field})" if field else ""))


class TimeoutError(AgentException):
    """Exception raised when an agent operation times out."""

    def __init__(self, message: str, agent_type: str = "Unknown", timeout: int = 0):
        self.timeout = timeout
        super().__init__(
            f"{message} (timeout: {timeout}s)" if timeout else message,
            agent_type=agent_type,
        )


class RepositoryError(IndexerError):
    """Exception raised when repository operations fail."""

    def __init__(self, message: str):
        super().__init__(f"Repository error: {message}")


class ParsingError(IndexerError):
    """Exception raised when AST parsing fails."""

    def __init__(self, message: str, file_path: str | None = None):
        self.file_path = file_path
        error_msg = f"Parsing error: {message}"
        if file_path:
            error_msg += f" (file: {file_path})"
        super().__init__(error_msg)
