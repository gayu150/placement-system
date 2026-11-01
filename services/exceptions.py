"""
Recruitment & Placement Management System
Custom Exception Classes
Provides domain-specific exceptions for business logic, validation, and transitions.
"""


class AppException(Exception):
    """Base exception for application errors."""
    def __init__(self, message="An application error occurred.", code=400):
        super().__init__(message)
        self.message = message
        self.code = code


class ValidationError(AppException):
    """Raised when client input fails business validation rules."""
    def __init__(self, message, errors=None):
        super().__init__(message, code=400)
        self.errors = errors or []


class DuplicateError(AppException):
    """Raised when unique constraints are violated (e.g. duplicate email, mobile, or application)."""
    def __init__(self, message="A record with these unique details already exists."):
        super().__init__(message, code=409)


class NotFoundError(AppException):
    """Raised when a requested resource is not found."""
    def __init__(self, message="Requested resource was not found."):
        super().__init__(message, code=404)


class StateTransitionError(AppException):
    """Raised when an illegal workflow state transition is attempted."""
    def __init__(self, message="Invalid state transition attempted."):
        super().__init__(message, code=422)


class EligibilityError(AppException):
    """Raised when candidate does not satisfy eligibility criteria without override."""
    def __init__(self, message="Candidate is not eligible for this job.", reasons=None):
        super().__init__(message, code=422)
        self.reasons = reasons or []


class AuthorizationError(AppException):
    """Raised when an authenticated user lacks permissions for an operation."""
    def __init__(self, message="You are not authorized to perform this action."):
        super().__init__(message, code=403)

