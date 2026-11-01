"""
Recruitment & Placement Management System
Company Management Service
"""

from dao import company_dao, activity_dao
from services.exceptions import ValidationError, NotFoundError


def validate_company_data(data, company_id=None):
    errors = []

    code = (data.get("company_code") or "").strip()
    if not code:
        errors.append("Company Code is required.")
    else:
        existing = company_dao.get_company_by_code(code)
        if existing and existing["company_id"] != company_id:
            errors.append(f"Company Code '{code}' is already assigned to another company.")

    name = (data.get("company_name") or "").strip()
    if not name:
        errors.append("Company Name is required.")

    industry = (data.get("industry") or "").strip()
    if not industry:
        errors.append("Industry is required.")

    location = (data.get("location") or "").strip()
    if not location:
        errors.append("Location is required.")

    hr_name = (data.get("hr_name") or "").strip()
    hr_email = (data.get("hr_email") or "").strip()
    hr_phone = (data.get("hr_phone") or "").strip()
    if not hr_name:
        errors.append("HR Contact Name is required.")
    if not hr_email:
        errors.append("HR Contact Email is required.")
    if not hr_phone:
        errors.append("HR Contact Phone is required.")

    if errors:
        raise ValidationError("; ".join(errors), errors=errors)


def create_company(data, user_id=None, user_name=None):
    validate_company_data(data)
    comp_id = company_dao.create_company(data)
    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Companies",
        action="CREATE",
        record_id=data.get("company_code"),
        description=f"Created company {data.get('company_name')} ({data.get('company_code')})"
    )
    return comp_id


def update_company(company_id, data, user_id=None, user_name=None):
    existing = company_dao.get_company_by_id(company_id)
    if not existing:
        raise NotFoundError(f"Company with ID #{company_id} not found.")

    validate_company_data(data, company_id=company_id)
    company_dao.update_company(company_id, data)
    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Companies",
        action="UPDATE",
        record_id=existing.get("company_code"),
        description=f"Updated company details for {data.get('company_name')}"
    )
    return True


def deactivate_company(company_id, user_id=None, user_name=None):
    """
    Soft-deactivates company instead of hard deletion to maintain job and recruitment integrity.
    """
    existing = company_dao.get_company_by_id(company_id)
    if not existing:
        raise NotFoundError(f"Company with ID #{company_id} not found.")

    company_dao.set_company_status(company_id, "Inactive")
    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Companies",
        action="DEACTIVATE",
        record_id=existing.get("company_code"),
        description=f"Deactivated company {existing.get('company_name')} ({existing.get('company_code')})"
    )
    return True


def activate_company(company_id, user_id=None, user_name=None):
    existing = company_dao.get_company_by_id(company_id)
    if not existing:
        raise NotFoundError(f"Company with ID #{company_id} not found.")

    company_dao.set_company_status(company_id, "Active")
    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Companies",
        action="ACTIVATE",
        record_id=existing.get("company_code"),
        description=f"Reactivated company {existing.get('company_name')}"
    )
    return True

