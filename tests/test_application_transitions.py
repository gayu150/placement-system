"""
Tests for Application Stage Transitions & Recruitment Pipeline State Machine
"""

import pytest
from services import application_service, exceptions
from dao import application_dao
from models.application import ApplicationStage


def test_valid_stage_progression():
    """Follows valid step-by-step pipeline transitions."""
    # Create application for Candidate 6 on Job 3 (Divya on Fintech)
    app_id = application_service.submit_application(candidate_id=6, job_id=3)
    app = application_dao.get_application_by_id(app_id)
    assert app["current_stage"] == ApplicationStage.APPLIED

    # 1. APPLIED -> ELIGIBILITY_VERIFIED
    application_service.transition_stage(app_id, ApplicationStage.ELIGIBILITY_VERIFIED)
    app = application_dao.get_application_by_id(app_id)
    assert app["current_stage"] == ApplicationStage.ELIGIBILITY_VERIFIED

    # 2. ELIGIBILITY_VERIFIED -> SHORTLISTED
    application_service.transition_stage(app_id, ApplicationStage.SHORTLISTED)
    app = application_dao.get_application_by_id(app_id)
    assert app["current_stage"] == ApplicationStage.SHORTLISTED

    # 3. SHORTLISTED -> INTERVIEW_SCHEDULED
    application_service.transition_stage(app_id, ApplicationStage.INTERVIEW_SCHEDULED)
    app = application_dao.get_application_by_id(app_id)
    assert app["current_stage"] == ApplicationStage.INTERVIEW_SCHEDULED

    # Verify history was recorded for each transition
    hist = application_dao.get_application_history(app_id)
    assert len(hist) >= 4  # Initial + 3 transitions


def test_invalid_stage_transition_blocked():
    """Illegal stage jumping must be blocked by StateTransitionError."""
    # App 2 is at INTERVIEW_SCHEDULED; jumping directly to JOINED is forbidden
    app = application_dao.get_application_by_id(2)

    with pytest.raises(exceptions.StateTransitionError) as exc_info:
        application_service.transition_stage(2, ApplicationStage.JOINED)
    assert "Cannot transition application" in str(exc_info.value)


def test_terminal_stages_block_further_transitions():
    """Once terminal (e.g. JOINED, REJECTED, WITHDRAWN), no further transitions allowed."""
    # App 1 is in JOINED stage
    app = application_dao.get_application_by_id(1)
    assert app["current_stage"] == ApplicationStage.JOINED

    with pytest.raises(exceptions.StateTransitionError):
        application_service.transition_stage(1, ApplicationStage.SHORTLISTED)
