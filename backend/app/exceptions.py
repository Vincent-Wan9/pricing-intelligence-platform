class DomainError(Exception):
    """Base class for errors safe to expose through the API."""

    default_code = "BUSINESS_OPERATION_INVALID"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code


class ResourceNotFoundError(DomainError):
    default_code = "RESOURCE_NOT_FOUND"


class ConflictError(DomainError):
    default_code = "RESOURCE_CONFLICT"


class ValidationError(DomainError):
    default_code = "VALIDATION_ERROR"


class AuthenticationError(DomainError):
    default_code = "INVALID_CREDENTIALS"


class AuthorizationError(DomainError):
    default_code = "INSUFFICIENT_PERMISSIONS"
