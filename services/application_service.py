"""
Recruitment & Placement Management System
Application Management & Workflow State Machine Service
"""

import time
import random
from models.application import ApplicationStage
from dao import application_dao, candidate_dao, job_dao, activity_dao
from services.eligibility_service import evaluate_eligibility
from services.exceptions import (
    ValidationError,
    DuplicateError,
    NotFoundError,
    EligibilityError,
    StateTransitionError
)


def generate_application_code():
    timestamp = int(time.time()) % 100000
    rand = random.randint(100, 999)
    return f"APP-{timestamp}-{rand}"


def submit_application(candidate_id, job_id, is_override=False, override_reason=None,
                       user_id=None, user_name=None):
    """
    Evaluates eligibility and creates application if eligible (or if authorized override is provided).
    Enforces duplicate prevention and writes initial history.
    """
    candidate = candidate_dao.get_candidate_by_id(candidate_id)
    if not candidate:
        raise NotFoundError(f"Candidate #{candidate_id} not found.")

    job = job_dao.get_job_by_id(job_id)
    if not job:
        raise NotFoundError(f"Job #{job_id} not found.")

    # Check for existing application
    existing = application_dao.get_application_by_candidate_and_job(candidate_id, job_id)
    if existing:
        raise DuplicateError(
            f"Candidate {candidate['first_name']} {candidate['last_name']} ({candidate['candidate_code']}) "
            f"has already applied for job '{job['title']}' ({existing['application_code']})."
        )

    # Evaluate eligibility
    result = evaluate_eligibility(candidate_id, job_id)

    if not result.is_eligible and not is_override:
        raise EligibilityError(
            f"Candidate does not meet eligibility criteria for '{job['title']}': {'; '.join(result.reasons)}",
            reasons=result.reasons
        )

    if not result.is_eligible and is_override:
        if not override_reason or not override_reason.strip():
            raise ValidationError("Override reason must be provided when overriding eligibility failure.")

    app_code = generate_application_code()
    app_data = {
        "application_code": app_code,
        "candidate_id": candidate_id,
        "job_id": job_id,
        "current_stage": ApplicationStage.APPLIED,
        "eligibility_status": result.status,
        "eligibility_remarks": result.formatted_remarks,
        "is_override": 1 if is_override else 0,
        "override_reason": override_reason if is_override else None,
        "override_by": user_id if is_override else None
    }

    initial_remarks = "Application submitted."
    if is_override:
        initial_remarks += f" [Authorized Staff Override: {override_reason}]"

    app_id = application_dao.create_application(app_data, user_id=user_id, initial_remarks=initial_remarks)

    # Update candidate placement status to 'In Process' if unplaced
    if candidate.get("placement_status") == "Unplaced":
        candidate_dao.set_candidate_placement_status(candidate_id, "In Process")

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Applications",
        action="APPLY",
        record_id=app_code,
        description=(
            f"Recorded application {app_code} for {candidate['first_name']} {candidate['last_name']} "
            f"for job '{job['title']}'. Eligibility: {result.status}"
            + (f" (Staff Override applied)" if is_override else "")
        )
    )

    return app_id


def transition_stage(application_id, new_stage, remarks=None, user_id=None, user_name=None):
    """
    Enforces valid stage transitions through the recruitment workflow state machine.
    """
    app = application_dao.get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Application #{application_id} not found.")

    current_stage = app["current_stage"]
    if new_stage not in ApplicationStage.ALL_STAGES:
        raise ValidationError(f"Unknown application stage: '{new_stage}'.")

    if current_stage == new_stage:
        return True

    # Validate transition
    if not ApplicationStage.is_valid_transition(current_stage, new_stage):
        allowed = ApplicationStage.TRANSITIONS.get(current_stage, [])
        allowed_str = ", ".join(allowed) if allowed else "None (Terminal Stage)"
        raise StateTransitionError(
            f"Cannot transition application from '{current_stage}' to '{new_stage}'. "
            f"Valid next stages from '{current_stage}' are: {allowed_str}"
        )

    # Update in database with history entry
    application_dao.update_application_stage(
        application_id=application_id,
        new_stage=new_stage,
        remarks=remarks or f"Stage transitioned from {current_stage} to {new_stage}.",
        user_id=user_id
    )

    # If application is rejected or withdrawn, and candidate has no other active applications, reset status
    if new_stage in [ApplicationStage.REJECTED, ApplicationStage.WITHDRAWN]:
        cand_id = app["candidate_id"]
        other_active = False
        apps = candidate_dao.get_candidate_applications(cand_id)
        for other in apps:
            if other["application_id"] != application_id and other["current_stage"] not in ["REJECTED", "WITHDRAWN", "JOINED"]:
                other_active = True
                break
        if not other_active:
            cand = candidate_dao.get_candidate_by_id(cand_id)
            if cand and cand["placement_status"] == "In Process":
                candidate_dao.set_candidate_placement_status(cand_id, "Unplaced")

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Applications",
        action="STAGE_CHANGE",
        record_id=app.get("application_code"),
        description=f"Transitioned {app.get('application_code')} from {current_stage} to {new_stage}. Remarks: {remarks or 'None'}"
    )

    return True

