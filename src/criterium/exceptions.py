class CriteriumError(Exception):
    """Base exception for criterium."""

class CollectionNotFoundError(CriteriumError):
    """Raised when a requested research collection does not exist."""

class ProductNotFoundError(CriteriumError):
    """Raised when a requested product does not exist."""

class SourceUrlAlreadyExistsError(CriteriumError):
    """Raised when attempting to add a product with a source_url that already exists."""
