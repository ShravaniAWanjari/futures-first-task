"""
Module: exceptions.py
Purpose: Centralized structured exception hierarchy.
Responsibilities: Standardize failure states for API translation and graceful degradation.
"""

class BasePlatformError(Exception):
    """Base exception for the orchestration platform."""
    pass

class ValidationError(BasePlatformError):
    """Raised when data fails structural or logical validation."""
    pass

class UnsafeQueryError(BasePlatformError):
    """Raised when an LLM generates a potentially destructive SQL query."""
    pass

class RetrievalError(BasePlatformError):
    """Raised when semantic retrieval or vector database access fails."""
    pass

class EmbeddingError(BasePlatformError):
    """Raised when text embedding generation fails."""
    pass

class IngestionError(BasePlatformError):
    """Raised when the automated CSV data ingestion fails structurally."""
    pass

class OrchestrationError(BasePlatformError):
    """Raised when the orchestrator fails to parse or assemble context."""
    pass

class ConfigurationError(BasePlatformError):
    """Raised when environment settings are missing or misconfigured."""
    pass
