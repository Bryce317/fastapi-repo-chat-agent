"""Response caching with TTL for agent responses."""

import hashlib
import time
from typing import Any, Dict, Optional

from config.logging_config import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class CacheEntry:
    """Represents a cache entry with TTL."""

    def __init__(self, value: Any, ttl: int):
        """Initialize cache entry.
        
        Args:
            value: Cached value.
            ttl: Time-to-live in seconds.
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if the cache entry has expired.
        
        Returns:
            True if expired, False otherwise.
        """
        return time.time() - self.created_at > self.ttl


class ResponseCache:
    """TTL-based cache for agent responses to avoid redundant processing."""

    def __init__(self, default_ttl: int = 3600):
        """Initialize response cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (1 hour).
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        logger.info(f"ResponseCache initialized with default_ttl={default_ttl}s")

    def _generate_key(self, query: str, context: Optional[str] = None) -> str:
        """Generate a cache key from query and context.
        
        Args:
            query: User query.
            context: Optional additional context.
            
        Returns:
            Cache key (hash).
        """
        key_data = query
        if context:
            key_data += f"|{context}"
        
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, query: str, context: Optional[str] = None) -> Optional[Any]:
        """Retrieve a cached response.
        
        Args:
            query: User query.
            context: Optional additional context.
            
        Returns:
            Cached value if found and not expired, None otherwise.
        """
        key = self._generate_key(query, context)
        
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        if entry.is_expired():
            del self._cache[key]
            logger.debug(f"Cache entry expired and removed: {key[:16]}...")
            return None
        
        logger.debug(f"Cache hit: {key[:16]}...")
        return entry.value

    def set(
        self,
        query: str,
        value: Any,
        context: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """Store a response in the cache.
        
        Args:
            query: User query.
            value: Response to cache.
            context: Optional additional context.
            ttl: Time-to-live in seconds (default: use default_ttl).
        """
        key = self._generate_key(query, context)
        ttl = ttl if ttl is not None else self.default_ttl
        
        self._cache[key] = CacheEntry(value, ttl)
        logger.debug(f"Cache set: {key[:16]}... (TTL: {ttl}s)")

    def invalidate(self, query: str, context: Optional[str] = None) -> bool:
        """Invalidate a specific cache entry.
        
        Args:
            query: User query.
            context: Optional additional context.
            
        Returns:
            True if entry was found and removed, False otherwise.
        """
        key = self._generate_key(query, context)
        
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated: {key[:16]}...")
            return True
        
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        entry_count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {entry_count} entries removed")

    def cleanup_expired(self) -> int:
        """Remove all expired cache entries.
        
        Returns:
            Number of entries removed.
        """
        expired_keys = [
            key for key, entry in self._cache.items() if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics.
        """
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "default_ttl": self.default_ttl,
        }


# Global response cache instance
_response_cache: Optional[ResponseCache] = None


def get_response_cache() -> ResponseCache:
    """Get or create the global response cache instance.
    
    Returns:
        ResponseCache instance.
    """
    global _response_cache
    
    if _response_cache is None:
        settings = get_settings()
        _response_cache = ResponseCache(default_ttl=settings.response_cache_ttl)
    
    return _response_cache
