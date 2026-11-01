"""
Recruitment & Placement Management System
Candidate Management Service
"""

import re
from dao import candidate_dao, activity_dao
from services.exceptions import ValidationError, DuplicateError, NotFoundError


EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


def validate_candidate_data(data, candidate_id=None):
    """Validates candidate fields and constraints."""
    errors = []

    # Code
    code = (data.get("candidate_code") or "").strip()
    if not code:
        errors.append("Candidate Code is required.")
    else:
        existing = candidate_dao.get_candidate_by_code(code)
        if existing and existing["candidate_id"] != candidate_id:
            errors.append(f"Candidate Code '{code}' is already assigned to another candidate.")

    # Name
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    if not first_name:
        errors.append("First Name is required.")
    if not last_name:
        errors.append("Last Name is required.")

    # Email
    email = (data.get("email") or "").strip()
    if not email:
        errors.append("Email is required.")
    elif not EMAIL_REGEX.match(email):
        errors.append("Invalid email address format.")
    else:
        existing = candidate_dao.get_candidate_by_email(email)
        if existing and existing["candidate_id"] != candidate_id:
            errors.append(f"Email '{email}' is already registered with another candidate.")

    # Mobile
    mobile = (data.get("mobile") or "").strip()
    if not mobile:
        errors.append("Mobile number is required.")
    elif len(re.sub(r"\D", "", mobile)) < 10:
        errors.append("Mobile number must contain at least 10 digits.")
    else:
        existing = candidate_dao.get_candidate_by_mobile(mobile)
        if existing and existing["candidate_id"] != candidate_id:
            errors.append(f"Mobile '{mobile}' is already in use by another candidate.")

    # Percentage
    try:
        pct = float(data.get("percentage", 0.0))
        if pct < 0.0 or pct > 100.0:
            errors.append("Percentage must be between 0.00 and 100.00.")
    except (ValueError, TypeError):
        errors.append("Percentage must be a valid numeric value.")

    # Backlogs
    try:
        backlogs = int(data.get("backlog_count", 0))
        if backlogs < 0:
            errors.append("Backlog count cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Backlog count must be a non-negative integer.")

    # Passing Year
    try:
        year = int(data.get("passing_year", 0))
        if year < 1990 or year > 2035:
            errors.append("Passing year must be a realistic year (e.g. 2020-2030).")
    except (ValueError, TypeError):
        errors.append("Passing year must be an integer.")

    # Qualification & Primary Tech
    if not (data.get("qualification") or "").strip():
        errors.append("Qualification is required.")
    if not (data.get("primary_technology") or "").strip():
        errors.append("Primary Technology is required.")

    if errors:
        raise ValidationError("; ".join(errors), errors=errors)


def create_candidate(data, skill_items=None, user_id=None, user_name=None):
    validate_candidate_data(data)
    candidate_id = candidate_dao.create_candidate(data, skill_items)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Candidates",
        action="CREATE",
        record_id=data.get("candidate_code"),
        description=f"Created candidate {data.get('first_name')} {data.get('last_name')} ({data.get('candidate_code')})"
    )
    return candidate_id


def update_candidate(candidate_id, data, skill_items=None, user_id=None, user_name=None):
    existing = candidate_dao.get_candidate_by_id(candidate_id)
    if not existing:
        raise NotFoundError(f"Candidate with ID #{candidate_id} not found.")

    validate_candidate_data(data, candidate_id=candidate_id)
    candidate_dao.update_candidate(candidate_id, data, skill_items)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Candidates",
        action="UPDATE",
        record_id=existing.get("candidate_code"),
        description=f"Updated candidate profile for {data.get('first_name')} {data.get('last_name')}"
    )
    return True


def deactivate_candidate(candidate_id, user_id=None, user_name=None):
    """
    Soft-deactivates candidate to preserve business and recruitment history.
    """
    existing = candidate_dao.get_candidate_by_id(candidate_id)
    if not existing:
        raise NotFoundError(f"Candidate with ID #{candidate_id} not found.")

    candidate_dao.set_candidate_status(candidate_id, "Inactive")
    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Candidates",
        action="DEACTIVATE",
        record_id=existing.get("candidate_code"),
        description=f"Deactivated candidate {existing.get('first_name')} {existing.get('last_name')} ({existing.get('candidate_code')})"
    )
    return True


def activate_candidate(candidate_id, user_id=None, user_name=None):
    existing = candidate_dao.get_candidate_by_id(candidate_id)
    if not existing:
        raise NotFoundError(f"Candidate with ID #{candidate_id} not found.")

    candidate_dao.set_candidate_status(candidate_id, "Active")
    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Candidates",
        action="ACTIVATE",
        record_id=existing.get("candidate_code"),
        description=f"Reactivated candidate {existing.get('first_name')} {existing.get('last_name')}"
    )
    return True

