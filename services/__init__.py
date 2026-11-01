"""
Recruitment & Placement Management System Services Package
"""

from services.exceptions import (
    AppException,
    ValidationError,
    DuplicateError,
    NotFoundError,
    EligibilityError,
    StateTransitionError,
    AuthorizationError,
)

__all__ = [
    "AppException",
    "ValidationError",
    "DuplicateError",
    "NotFoundError",
    "EligibilityError",
    "StateTransitionError",
    "AuthorizationError",
]

