"""Conversation memory management for multi-turn interactions."""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from config.logging_config import get_logger
from config.settings import get_settings
from core.models import Message

logger = get_logger(__name__)


class ConversationMemory:
    """Manages conversation history per session with context window management."""

    def __init__(self, max_history: int = 20):
        """Initialize conversation memory.
        
        Args:
            max_history: Maximum number of messages to keep per session.
        """
        self.max_history = max_history
        self._conversations: Dict[str, List[Message]] = defaultdict(list)
        logger.info(f"ConversationMemory initialized with max_history={max_history}")

    def add_message(self, session_id: str, message: Message) -> None:
        """Add a message to the conversation history.
        
        Args:
            session_id: Session identifier.
            message: Message to add.
        """
        self._conversations[session_id].append(message)
        
        # Trim history if it exceeds max_history
        if len(self._conversations[session_id]) > self.max_history:
            removed = self._conversations[session_id].pop(0)
            logger.debug(
                f"Trimmed conversation history for session {session_id}: "
                f"removed message from {removed.timestamp}"
            )

    def add_user_message(self, session_id: str, content: str) -> Message:
        """Add a user message to the conversation.
        
        Args:
            session_id: Session identifier.
            content: Message content.
            
        Returns:
            Created Message object.
        """
        message = Message(role="user", content=content)
        self.add_message(session_id, message)
        logger.debug(f"Added user message to session {session_id}")
        return message

    def add_assistant_message(self, session_id: str, content: str) -> Message:
        """Add an assistant message to the conversation.
        
        Args:
            session_id: Session identifier.
            content: Message content.
            
        Returns:
            Created Message object.
        """
        message = Message(role="assistant", content=content)
        self.add_message(session_id, message)
        logger.debug(f"Added assistant message to session {session_id}")
        return message

    def get_history(
        self, session_id: str, last_n: Optional[int] = None
    ) -> List[Message]:
        """Get conversation history for a session.
        
        Args:
            session_id: Session identifier.
            last_n: Number of recent messages to retrieve (default: all).
            
        Returns:
            List of messages in chronological order.
        """
        messages = self._conversations.get(session_id, [])
        
        if last_n is not None:
            messages = messages[-last_n:]
        
        return messages

    def get_context_window(self, session_id: str, window_size: int = 10) -> List[Message]:
        """Get recent context window for a session.
        
        Args:
            session_id: Session identifier.
            window_size: Number of recent messages to include.
            
        Returns:
            List of recent messages.
        """
        return self.get_history(session_id, last_n=window_size)

    def format_for_llm(self, session_id: str, last_n: int = 10) -> List[Dict[str, str]]:
        """Format conversation history for LLM consumption.
        
        Args:
            session_id: Session identifier.
            last_n: Number of recent messages to include.
            
        Returns:
            List of message dictionaries with 'role' and 'content' keys.
        """
        messages = self.get_history(session_id, last_n)
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session.
        
        Args:
            session_id: Session identifier.
        """
        if session_id in self._conversations:
            message_count = len(self._conversations[session_id])
            del self._conversations[session_id]
            logger.info(f"Cleared {message_count} messages from session {session_id}")

    def get_session_count(self) -> int:
        """Get the number of active sessions.
        
        Returns:
            Number of sessions.
        """
        return len(self._conversations)

    def get_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session.
        
        Args:
            session_id: Session identifier.
            
        Returns:
            Number of messages.
        """
        return len(self._conversations.get(session_id, []))


# Global conversation memory instance
_conversation_memory: Optional[ConversationMemory] = None


def get_conversation_memory() -> ConversationMemory:
    """Get or create the global conversation memory instance.
    
    Returns:
        ConversationMemory instance.
    """
    global _conversation_memory
    
    if _conversation_memory is None:
        settings = get_settings()
        _conversation_memory = ConversationMemory(
            max_history=settings.max_conversation_history
        )
    
    return _conversation_memory
