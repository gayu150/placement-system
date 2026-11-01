"""
Recruitment & Placement Management System
Job Model
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class Job:
    job_id: Optional[int] = None
    job_code: str = ""
    company_id: int = 0
    title: str = ""
    employment_type: str = "Full-time"
    location: str = ""
    openings: int = 1
    min_package: float = 0.0
    max_package: float = 0.0
    qualification_req: str = "Any"
    min_percentage: float = 60.0
    min_passing_year: int = 2024
    max_passing_year: int = 2026
    max_backlogs: int = 0
    experience_req: float = 0.0
    posted_date: str = ""
    deadline: str = ""
    status: str = "Open"
    created_by: Optional[int] = None
    company_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    skills: List[Dict] = field(default_factory=list)

