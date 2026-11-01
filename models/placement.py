"""
Recruitment & Placement Management System
Placement Model
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Placement:
    placement_id: Optional[int] = None
    placement_code: str = ""
    offer_id: int = 0
    candidate_id: int = 0
    company_id: int = 0
    job_id: int = 0
    designation: str = ""
    final_package_lpa: float = 0.0
    expected_joining_date: str = ""
    actual_joining_date: Optional[str] = None
    joining_status: str = "PENDING"
    remarks: Optional[str] = None
    recorded_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

