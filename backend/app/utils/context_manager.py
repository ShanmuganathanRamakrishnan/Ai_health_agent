"""
Conversational Context Manager (Short-term Memory).
Tracks the last active patient for pronoun resolution in follow-up queries.

Memory is in-memory only, not persisted to DB.
"""
from typing import Optional
from threading import Lock
from datetime import datetime


class ConversationContext:
    """
    Thread-safe in-memory store for conversational context.
    Tracks the last successfully identified patient and query type.
    
    Memory contents:
    - last_patient_id: int
    - last_patient_name: str
    - last_patient_gender: str
    - last_query_type: str (FACTUAL, SUMMARY, COMPLEX)
    - timestamp: datetime
    """
    
    # Memory expiry in seconds (30 minutes)
    MEMORY_EXPIRY_SECONDS = 1800
    
    def __init__(self):
        self._last_patient_id: Optional[int] = None
        self._last_patient_name: Optional[str] = None
        self._last_patient_gender: Optional[str] = None
        self._last_query_type: Optional[str] = None
        self._timestamp: Optional[datetime] = None
        self._lock = Lock()
    
    def set_active_patient(
        self,
        patient_id: int,
        patient_name: str,
        patient_gender: Optional[str] = None,
        query_type: Optional[str] = None
    ) -> None:
        """
        Store the currently active patient for follow-up reference.
        """
        with self._lock:
            self._last_patient_id = patient_id
            self._last_patient_name = patient_name
            self._last_patient_gender = patient_gender
            self._last_query_type = query_type
            self._timestamp = datetime.now()
    
    def get_active_patient_id(self) -> Optional[int]:
        """Get the last active patient ID."""
        with self._lock:
            if self._is_expired():
                return None
            return self._last_patient_id
    
    def get_active_patient_name(self) -> Optional[str]:
        """Get the last active patient name."""
        with self._lock:
            if self._is_expired():
                return None
            return self._last_patient_name
    
    def get_active_patient_gender(self) -> Optional[str]:
        """Get the last active patient gender."""
        with self._lock:
            if self._is_expired():
                return None
            return self._last_patient_gender
    
    def get_last_query_type(self) -> Optional[str]:
        """Get the last query type."""
        with self._lock:
            if self._is_expired():
                return None
            return self._last_query_type
    
    def get_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of last memory update."""
        with self._lock:
            return self._timestamp
    
    def _is_expired(self) -> bool:
        """Check if memory has expired (not thread-safe, call within lock)."""
        if self._timestamp is None:
            return True
        elapsed = (datetime.now() - self._timestamp).total_seconds()
        return elapsed > self.MEMORY_EXPIRY_SECONDS
    
    def clear(self) -> None:
        """Clear the context."""
        with self._lock:
            self._last_patient_id = None
            self._last_patient_name = None
            self._last_patient_gender = None
            self._last_query_type = None
            self._timestamp = None
    
    def has_active_patient(self) -> bool:
        """Check if there's an active patient in context (not expired)."""
        with self._lock:
            if self._is_expired():
                return False
            return self._last_patient_id is not None
    
    def get_memory_summary(self) -> dict:
        """Get a summary of current memory state for debugging."""
        with self._lock:
            return {
                "patient_id": self._last_patient_id,
                "patient_name": self._last_patient_name,
                "patient_gender": self._last_patient_gender,
                "query_type": self._last_query_type,
                "timestamp": self._timestamp.isoformat() if self._timestamp else None,
                "expired": self._is_expired(),
            }


# Global singleton for conversation context
# In production, this should be session-scoped
_context = ConversationContext()


def get_context() -> ConversationContext:
    """Get the global conversation context."""
    return _context
