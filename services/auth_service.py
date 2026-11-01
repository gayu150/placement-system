"""
Recruitment & Placement Management System
Authentication & Session Service
"""

from werkzeug.security import generate_password_hash, check_password_hash
from dao.user_dao import get_user_by_username, get_user_by_id
from services.exceptions import ValidationError, AuthorizationError


def hash_password(plaintext_password):
    """Hash password securely using scrypt/pbkdf2."""
    if not plaintext_password or len(plaintext_password) < 6:
        raise ValidationError("Password must be at least 6 characters long.")
    return generate_password_hash(plaintext_password)


def verify_password(plaintext_password, password_hash):
    """Verify password against stored hash."""
    if not plaintext_password or not password_hash:
        return False
    return check_password_hash(password_hash, plaintext_password)


def authenticate_user(username, password):
    """
    Authenticate user by username and password.
    Returns user dict on success, None on invalid credentials.
    Raises ValidationError if inactive.
    """
    if not username or not password:
        raise ValidationError("Username and password are required.")

    user = get_user_by_username(username.strip())
    if not user:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    if not user["is_active"]:
        raise ValidationError("This account is currently deactivated. Please contact an Administrator.")

    return user

