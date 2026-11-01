"""
Recruitment & Placement Management System
Candidate Model
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class Candidate:
    candidate_id: Optional[int] = None
    candidate_code: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    mobile: str = ""
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    qualification: str = ""
    college: str = ""
    university: str = ""
    passing_year: int = 0
    percentage: float = 0.0
    cgpa: Optional[float] = None
    backlog_count: int = 0
    primary_technology: str = ""
    skill_proficiency: str = "Intermediate"
    experience_years: float = 0.0
    current_location: str = ""
    preferred_location: str = ""
    profile_status: str = "Active"
    placement_status: str = "Unplaced"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    skills: List[Dict] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

