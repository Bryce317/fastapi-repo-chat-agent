"""Helper utilities for the multi-agent system."""

import asyncio
import re
import uuid
from functools import wraps
from typing import Any, Callable, TypeVar

from config.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Decorator to retry async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for delay after each retry.
        exceptions: Tuple of exception types to catch and retry.
        
    Returns:
        Decorated function.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for "
                            f"{func.__name__}: {e}. Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}"
                        )
            
            # If we get here, all retries failed
            raise last_exception

        return wrapper

    return decorator


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing.
    
    Returns:
        UUID string without hyphens.
    """
    return uuid.uuid4().hex[:16]


def sanitize_code(code: str) -> str:
    """Sanitize code by removing excessive whitespace and empty lines.
    
    Args:
        code: Raw code string.
        
    Returns:
        Sanitized code string.
    """
    # Remove multiple consecutive empty lines
    code = re.sub(r'\n\s*\n\s*\n', '\n\n', code)
    
    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in code.split('\n')]
    
    # Join back and strip leading/trailing whitespace
    return '\n'.join(lines).strip()


def extract_imports(code: str) -> list[str]:
    """Extract import statements from Python code.
    
    Args:
        code: Python source code.
        
    Returns:
        List of import statements.
    """
    import_pattern = r'^(?:from\s+[\w.]+\s+)?import\s+.*$'
    imports = []
    
    for line in code.split('\n'):
        line = line.strip()
        if re.match(import_pattern, line):
            imports.append(line)
    
    return imports


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to a maximum length.
    
    Args:
        text: Text to truncate.
        max_length: Maximum length (including suffix).
        suffix: Suffix to add when truncating.
        
    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    
    return text[: max_length - len(suffix)] + suffix


def format_file_path(path: str) -> str:
    """Format file path for display (remove common prefixes).
    
    Args:
        path: File path.
        
    Returns:
        Formatted path.
    """
    # Remove common repository prefixes
    path = re.sub(r'^.*?/fastapi/', 'fastapi/', path)
    return path


def extract_function_signature(code: str) -> str | None:
    """Extract function signature from code.
    
    Args:
        code: Python function code.
        
    Returns:
        Function signature or None if not found.
    """
    # Match function definition
    match = re.search(r'^(?:async\s+)?def\s+\w+\([^)]*\)(?:\s*->\s*[^:]+)?:', code, re.MULTILINE)
    
    if match:
        return match.group(0).rstrip(':').strip()
    
    return None


def parse_cypher_result(result: list[dict]) -> list[dict]:
    """Parse Neo4j Cypher query results to extract node/relationship data.
    
    Args:
        result: Raw Cypher query result.
        
    Returns:
        Parsed result with simplified structure.
    """
    parsed = []
    
    for record in result:
        parsed_record = {}
        
        for key, value in record.items():
            # Handle Neo4j node/relationship objects
            if hasattr(value, '__dict__'):
                parsed_record[key] = dict(value)
            else:
                parsed_record[key] = value
        
        parsed.append(parsed_record)
    
    return parsed
