"""
Recruitment & Placement Management System
Offer Model
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Offer:
    offer_id: Optional[int] = None
    offer_code: str = ""
    application_id: int = 0
    candidate_id: int = 0
    company_id: int = 0
    job_id: int = 0
    designation: str = ""
    package_lpa: float = 0.0
    offer_date: str = ""
    expected_joining_date: str = ""
    status: str = "OFFERED"
    remarks: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

