"""
Recruitment & Placement Management System
Company Model
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Company:
    company_id: Optional[int] = None
    company_code: str = ""
    company_name: str = ""
    industry: str = ""
    website: Optional[str] = None
    location: str = ""
    company_type: str = "Service"
    hr_name: str = ""
    hr_email: str = ""
    hr_phone: str = ""
    status: str = "Active"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

