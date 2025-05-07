"""Custom exception classes for the VANTA Seed Data Catalog and related services."""

class DataCatalogException(Exception):
    """Base exception for all Data Catalog errors."""
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.message = message

    def __str__(self):
        if self.original_exception:
            return f"{self.message} (Caused by: {type(self.original_exception).__name__} - {str(self.original_exception)})"
        return self.message

class NotFound(DataCatalogException):
    """Raised when a requested item is not found in the data catalog."""
    pass

class StorageFailure(DataCatalogException):
    """Raised when an underlying storage operation (e.g., Qdrant) fails unexpectedly.
       This typically wraps a more specific connection or operation error from the storage client.
    """
    pass

class ConnectionFailure(StorageFailure):
    """Raised specifically for storage connection issues."""
    pass

class OperationFailure(StorageFailure):
    """Raised for non-connection related storage operation failures."""
    pass

class ConfigurationError(DataCatalogException):
    """Raised for configuration-related issues within the catalog or its components."""
    pass

class EmbeddingError(DataCatalogException):
    """Raised when there's an error during the embedding generation process."""
    pass

class ValidationError(DataCatalogException):
    """Raised when input data fails validation (e.g., Pydantic model validation)."""
    pass

# Example of how Qdrant-specific exceptions from the adapter might be mapped or used:
# from vanta_seed.utils.exceptions import QdrantConnectionError, QdrantOperationError 
# These could be caught and re-raised as ConnectionFailure/OperationFailure if desired for abstraction
# or the Qdrant-specific ones can be allowed to propagate if more detail is needed. 