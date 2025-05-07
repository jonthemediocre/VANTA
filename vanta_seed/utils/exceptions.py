"""Custom exception classes for the VANTA Seed project."""

class VantaBaseException(Exception):
    """Base exception for all custom exceptions in the VANTA project."""
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.message = message

    def __str__(self):
        if self.original_exception:
            return f"{self.message}: {type(self.original_exception).__name__} - {str(self.original_exception)}"
        return self.message

class QdrantInteractionError(VantaBaseException):
    """Base class for errors during interaction with Qdrant."""
    pass

class QdrantConnectionError(QdrantInteractionError):
    """Raised when there's an issue connecting to Qdrant."""
    pass

class QdrantOperationError(QdrantInteractionError):
    """Raised when a Qdrant operation (upsert, search, delete, etc.) fails for reasons other than connection.
       This could include issues with data, collection state, or Qdrant internal errors.
    """
    pass

class QdrantDataNotFoundError(QdrantInteractionError):
    """Raised specifically when an expected data point or collection is not found in Qdrant.
       Note: Many get/find methods might return None instead of raising this directly.
       This can be used if an operation *requires* data to exist before proceeding.
    """
    pass

class EmbeddingError(VantaBaseException):
    """Raised when there's an error during the embedding generation process."""
    pass

class ConfigurationError(VantaBaseException):
    """Raised for configuration-related issues."""
    pass 