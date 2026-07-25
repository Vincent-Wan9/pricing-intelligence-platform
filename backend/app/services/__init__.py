"""Shared service-layer exceptions."""


class ProductServiceError(Exception):
    """Base exception for product business-logic errors."""


class ProductNotFoundError(ProductServiceError):
    """Raised when a requested product does not exist."""


class ProductConflictError(ProductServiceError):
    """Raised when product data conflicts with an existing record."""


class ProductValidationError(ProductServiceError):
    """Raised when product data violates a business rule."""


class ProductAuthorizationError(ProductServiceError):
    """Raised when a user cannot perform a product operation."""
