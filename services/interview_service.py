"""
Recruitment & Placement Management System
Interview Scheduling & Feedback Service
"""

from dao import interview_dao, application_dao, activity_dao
from services.exceptions import ValidationError, NotFoundError, DuplicateError


def schedule_interview_round(data, user_id=None, user_name=None):
    """Schedules a new interview round."""
    errors = []
    app_id = data.get("application_id")
    if not app_id:
        errors.append("Application selection is required.")
    else:
        app = application_dao.get_application_by_id(app_id)
        if not app:
            errors.append(f"Application #{app_id} not found.")
        elif app["current_stage"] in ["REJECTED", "WITHDRAWN", "JOINED"]:
            errors.append(f"Cannot schedule interview for application in '{app['current_stage']}' stage.")

    if not data.get("round_name"):
        errors.append("Round Name is required (e.g. Technical, HR).")
    if not data.get("scheduled_date"):
        errors.append("Scheduled Date is required.")
    if not data.get("scheduled_time"):
        errors.append("Scheduled Time is required.")
    if not data.get("interviewer_name"):
        errors.append("Interviewer Name is required.")
    if not data.get("meeting_link_or_venue"):
        errors.append("Meeting Link or Venue is required.")

    if errors:
        raise ValidationError("; ".join(errors), errors=errors)

    # Determine next round number if not specified
    existing_rounds = interview_dao.get_interviews_by_application(app_id)
    next_num = len(existing_rounds) + 1
    data["round_number"] = int(data.get("round_number") or next_num)
    data["scheduled_by"] = user_id

    interview_id = interview_dao.schedule_interview(data)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Interviews",
        action="SCHEDULE",
        record_id=f"INT-{interview_id}",
        description=f"Scheduled Round #{data['round_number']} ({data['round_name']}) for application #{app_id}"
    )

    return interview_id


def reschedule_interview_round(interview_id, new_date, new_time, link_or_venue=None,
                              user_id=None, user_name=None):
    interview = interview_dao.get_interview_by_id(interview_id)
    if not interview:
        raise NotFoundError(f"Interview round #{interview_id} not found.")

    if not new_date or not new_time:
        raise ValidationError("Both new scheduled date and time are required for rescheduling.")

    interview_dao.reschedule_interview(interview_id, new_date, new_time, link_or_venue)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Interviews",
        action="RESCHEDULE",
        record_id=f"INT-{interview_id}",
        description=f"Rescheduled interview #{interview_id} to {new_date} at {new_time}"
    )
    return True


def update_interview_status(interview_id, new_status, user_id=None, user_name=None):
    valid_statuses = ["SCHEDULED", "COMPLETED", "CANCELLED", "NO_SHOW", "RESCHEDULED"]
    if new_status not in valid_statuses:
        raise ValidationError(f"Invalid status '{new_status}'. Allowed: {', '.join(valid_statuses)}")

    interview = interview_dao.get_interview_by_id(interview_id)
    if not interview:
        raise NotFoundError(f"Interview round #{interview_id} not found.")

    interview_dao.update_interview_status(interview_id, new_status)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Interviews",
        action="STATUS_CHANGE",
        record_id=f"INT-{interview_id}",
        description=f"Updated interview #{interview_id} status to {new_status}"
    )
    return True


def submit_interview_feedback(data, user_id=None, user_name=None):
    interview_id = data.get("interview_id")
    if not interview_id:
        raise ValidationError("Interview ID is required.")

    interview = interview_dao.get_interview_by_id(interview_id)
    if not interview:
        raise NotFoundError(f"Interview round #{interview_id} not found.")

    # Check if already has feedback
    existing = interview_dao.get_feedback_by_interview_id(interview_id)
    if existing:
        raise DuplicateError(f"Feedback has already been submitted for interview #{interview_id}.")

    # Validate ratings (1-5)
    errors = []
    for field_name in ["technical_rating", "communication_rating", "problem_solving_rating", "overall_rating"]:
        try:
            val = int(data.get(field_name, 0))
            if val < 1 or val > 5:
                errors.append(f"{field_name.replace('_', ' ').title()} must be between 1 and 5.")
        except (ValueError, TypeError):
            errors.append(f"{field_name.replace('_', ' ').title()} must be an integer between 1 and 5.")

    recom = data.get("recommendation")
    valid_recoms = ["NEXT_ROUND", "SELECTED", "REJECTED", "ON_HOLD"]
    if recom not in valid_recoms:
        errors.append(f"Recommendation must be one of: {', '.join(valid_recoms)}")

    if not (data.get("remarks") or "").strip():
        errors.append("Interview feedback remarks are required.")

    if errors:
        raise ValidationError("; ".join(errors), errors=errors)

    data["submitted_by"] = user_id
    feedback_id = interview_dao.record_feedback(data)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Interviews",
        action="FEEDBACK",
        record_id=f"INT-{interview_id}",
        description=f"Recorded feedback for Round #{interview['round_number']} ({recom})"
    )

    return feedback_id

