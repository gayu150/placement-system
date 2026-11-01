"""
Recruitment & Placement Management System
Job Management Service
"""

from datetime import datetime, date
from dao import job_dao, company_dao, activity_dao
from services.exceptions import ValidationError, NotFoundError


def _parse_date(val):
    if not val:
        return None
    if isinstance(val, (date, datetime)):
        return val if isinstance(val, date) else val.date()
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def validate_job_data(data, job_id=None):
    errors = []

    # Code
    code = (data.get("job_code") or "").strip()
    if not code:
        errors.append("Job Code is required.")
    else:
        existing = job_dao.get_job_by_code(code)
        if existing and existing["job_id"] != job_id:
            errors.append(f"Job Code '{code}' is already assigned to another job.")

    # Company existence and active check
    try:
        company_id = int(data.get("company_id", 0))
        company = company_dao.get_company_by_id(company_id)
        if not company:
            errors.append(f"Company ID #{company_id} does not exist.")
        elif company["status"] != "Active":
            errors.append(f"Cannot post jobs for inactive company '{company['company_name']}'.")
    except (ValueError, TypeError):
        errors.append("Valid Company selection is required.")

    # Title & Location
    if not (data.get("title") or "").strip():
        errors.append("Job Title is required.")
    if not (data.get("location") or "").strip():
        errors.append("Job Location is required.")

    # Openings
    try:
        openings = int(data.get("openings", 0))
        if openings <= 0:
            errors.append("Openings count must be greater than zero.")
    except (ValueError, TypeError):
        errors.append("Openings count must be an integer greater than zero.")

    # Package bounds
    try:
        min_pkg = float(data.get("min_package", 0.0))
        max_pkg = float(data.get("max_package", 0.0))
        if min_pkg < 0 or max_pkg < 0:
            errors.append("Package amounts cannot be negative.")
        elif min_pkg > max_pkg:
            errors.append("Minimum package cannot exceed maximum package.")
    except (ValueError, TypeError):
        errors.append("Packages must be valid numbers.")

    # Dates
    posted = _parse_date(data.get("posted_date"))
    deadline = _parse_date(data.get("deadline"))
    if not posted:
        errors.append("Valid Posted Date (YYYY-MM-DD) is required.")
    if not deadline:
        errors.append("Valid Deadline Date (YYYY-MM-DD) is required.")
    if posted and deadline and deadline < posted:
        errors.append("Deadline cannot be before the posted date.")

    # Passing Year bounds
    try:
        min_yr = int(data.get("min_passing_year", 0))
        max_yr = int(data.get("max_passing_year", 0))
        if min_yr > max_yr:
            errors.append("Minimum passing year cannot exceed maximum passing year.")
    except (ValueError, TypeError):
        errors.append("Passing years must be valid integers.")

    # Percentage
    try:
        min_pct = float(data.get("min_percentage", 60.0))
        if min_pct < 0 or min_pct > 100:
            errors.append("Minimum percentage must be between 0 and 100.")
    except (ValueError, TypeError):
        errors.append("Minimum percentage must be a number.")

    # Backlogs
    try:
        max_b = int(data.get("max_backlogs", 0))
        if max_b < 0:
            errors.append("Maximum allowed backlogs cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Maximum backlogs must be a non-negative integer.")

    if errors:
        raise ValidationError("; ".join(errors), errors=errors)


def create_job(data, skill_requirements=None, user_id=None, user_name=None):
    validate_job_data(data)
    data["created_by"] = user_id
    job_id = job_dao.create_job(data, skill_requirements)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Jobs",
        action="CREATE",
        record_id=data.get("job_code"),
        description=f"Created job opening '{data.get('title')}' ({data.get('job_code')})"
    )
    return job_id


def update_job(job_id, data, skill_requirements=None, user_id=None, user_name=None):
    existing = job_dao.get_job_by_id(job_id)
    if not existing:
        raise NotFoundError(f"Job with ID #{job_id} not found.")

    validate_job_data(data, job_id=job_id)
    job_dao.update_job(job_id, data, skill_requirements)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Jobs",
        action="UPDATE",
        record_id=existing.get("job_code"),
        description=f"Updated job details for '{data.get('title')}' ({existing.get('job_code')})"
    )
    return True


def change_job_status(job_id, new_status, user_id=None, user_name=None):
    """
    Closes or cancels jobs instead of deleting them to retain application history.
    """
    valid_statuses = ["Draft", "Open", "Closed", "Cancelled"]
    if new_status not in valid_statuses:
        raise ValidationError(f"Invalid status '{new_status}'. Allowed: {', '.join(valid_statuses)}")

    existing = job_dao.get_job_by_id(job_id)
    if not existing:
        raise NotFoundError(f"Job with ID #{job_id} not found.")

    job_dao.update_job_status(job_id, new_status)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Jobs",
        action="STATUS_CHANGE",
        record_id=existing.get("job_code"),
        description=f"Changed status of job '{existing.get('title')}' from {existing.get('status')} to {new_status}"
    )
    return True

