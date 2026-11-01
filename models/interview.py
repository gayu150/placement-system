"""
Recruitment & Placement Management System
Interview & Feedback Models
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class InterviewRound:
    interview_id: Optional[int] = None
    application_id: int = 0
    round_number: int = 1
    round_name: str = "Technical"
    scheduled_date: str = ""
    scheduled_time: str = ""
    interview_mode: str = "Online"
    interviewer_name: str = ""
    meeting_link_or_venue: str = ""
    status: str = "SCHEDULED"
    scheduled_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class InterviewFeedback:
    feedback_id: Optional[int] = None
    interview_id: int = 0
    technical_rating: int = 3
    communication_rating: int = 3
    problem_solving_rating: int = 3
    overall_rating: int = 3
    recommendation: str = "NEXT_ROUND"
    remarks: str = ""
    submitted_by: Optional[int] = None
    submitted_at: Optional[str] = None

