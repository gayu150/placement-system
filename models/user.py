"""
Recruitment & Placement Management System
User & Role Models
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Role:
    role_id: int
    role_name: str
    description: Optional[str] = None


@dataclass
class User:
    user_id: Optional[int] = None
    role_id: int = 2
    username: str = ""
    email: str = ""
    password_hash: str = ""
    full_name: str = ""
    is_active: bool = True
    role_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

