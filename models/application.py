"""
Recruitment & Placement Management System
Application Model & Stage State Machine
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


class ApplicationStage:
    APPLIED = "APPLIED"
    ELIGIBILITY_VERIFIED = "ELIGIBILITY_VERIFIED"
    SHORTLISTED = "SHORTLISTED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    INTERVIEWED = "INTERVIEWED"
    SELECTED = "SELECTED"
    OFFERED = "OFFERED"
    JOINED = "JOINED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"

    ALL_STAGES = [
        APPLIED,
        ELIGIBILITY_VERIFIED,
        SHORTLISTED,
        INTERVIEW_SCHEDULED,
        INTERVIEWED,
        SELECTED,
        OFFERED,
        JOINED,
        REJECTED,
        WITHDRAWN
    ]

    # Explicit state machine enforcing valid progression
    TRANSITIONS: Dict[str, List[str]] = {
        APPLIED: [ELIGIBILITY_VERIFIED, REJECTED, WITHDRAWN],
        ELIGIBILITY_VERIFIED: [SHORTLISTED, REJECTED, WITHDRAWN],
        SHORTLISTED: [INTERVIEW_SCHEDULED, REJECTED, WITHDRAWN],
        INTERVIEW_SCHEDULED: [INTERVIEWED, REJECTED, WITHDRAWN],
        INTERVIEWED: [INTERVIEW_SCHEDULED, SELECTED, REJECTED, WITHDRAWN],
        SELECTED: [OFFERED, REJECTED, WITHDRAWN],
        OFFERED: [JOINED, REJECTED, WITHDRAWN],
        JOINED: [],      # Terminal
        REJECTED: [],    # Terminal
        WITHDRAWN: []    # Terminal
    }

    @classmethod
    def is_valid_transition(cls, current_stage: str, next_stage: str) -> bool:
        """Check if transitioning from current_stage to next_stage is permitted."""
        allowed = cls.TRANSITIONS.get(current_stage, [])
        return next_stage in allowed


@dataclass
class EligibilityResult:
    """Represents the outcome of checking a candidate against job criteria."""
    is_eligible: bool
    reasons: List[str] = field(default_factory=list)
    status: str = field(init=False)

    def __post_init__(self):
        self.status = "ELIGIBLE" if self.is_eligible else "NOT_ELIGIBLE"

    @property
    def formatted_remarks(self) -> str:
        if self.is_eligible:
            return "Eligible: " + ("; ".join(self.reasons) if self.reasons else "All criteria satisfied.")
        return "Not Eligible: " + "; ".join(self.reasons)


@dataclass
class Application:
    application_id: Optional[int] = None
    application_code: str = ""
    candidate_id: int = 0
    job_id: int = 0
    applied_date: Optional[str] = None
    current_stage: str = ApplicationStage.APPLIED
    eligibility_status: str = "ELIGIBLE"
    eligibility_remarks: Optional[str] = None
    is_override: bool = False
    override_reason: Optional[str] = None
    override_by: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

