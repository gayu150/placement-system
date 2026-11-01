"""
Recruitment & Placement Management System
Offer & Placement Workflow Service
Handles transactional offer generation, acceptance, joining, and status synchronization.
"""

import time
import random
from dao import offer_dao, placement_dao, application_dao, candidate_dao, activity_dao
from services.exceptions import ValidationError, NotFoundError, DuplicateError, StateTransitionError


def generate_offer_code():
    timestamp = int(time.time()) % 100000
    rand = random.randint(100, 999)
    return f"OFF-{timestamp}-{rand}"


def generate_placement_code():
    timestamp = int(time.time()) % 100000
    rand = random.randint(100, 999)
    return f"PLC-{timestamp}-{rand}"


def create_offer(data, user_id=None, user_name=None):
    """
    Creates an offer for an application in SELECTED stage.
    Ensures only one offer per application and updates stage to OFFERED in a transaction.
    """
    app_id = data.get("application_id")
    if not app_id:
        raise ValidationError("Application ID is required.")

    app = application_dao.get_application_by_id(app_id)
    if not app:
        raise NotFoundError(f"Application #{app_id} not found.")

    if app["current_stage"] not in ["SELECTED", "INTERVIEWED"]:
        raise StateTransitionError(
            f"Cannot issue offer to an application in '{app['current_stage']}' stage. "
            f"Candidate must be in 'SELECTED' stage first."
        )

    # Check existing offer
    existing = offer_dao.get_offer_by_application_id(app_id)
    if existing:
        raise DuplicateError(f"An offer ({existing['offer_code']}) already exists for application #{app_id}.")

    # Validate fields
    errors = []
    designation = (data.get("designation") or "").strip()
    if not designation:
        errors.append("Designation is required.")

    try:
        pkg = float(data.get("package_lpa", 0.0))
        if pkg <= 0:
            errors.append("Offered package (CTC in LPA) must be greater than zero.")
    except (ValueError, TypeError):
        errors.append("Package LPA must be a valid number.")

    if not data.get("offer_date"):
        errors.append("Offer Date is required.")
    if not data.get("expected_joining_date"):
        errors.append("Expected Joining Date is required.")

    if errors:
        raise ValidationError("; ".join(errors), errors=errors)

    offer_code = generate_offer_code()
    offer_payload = {
        "offer_code": offer_code,
        "application_id": app_id,
        "candidate_id": app["candidate_id"],
        "company_id": app["company_id"],
        "job_id": app["job_id"],
        "designation": designation,
        "package_lpa": pkg,
        "offer_date": data["offer_date"],
        "expected_joining_date": data["expected_joining_date"],
        "status": "OFFERED",
        "remarks": data.get("remarks"),
        "created_by": user_id
    }

    offer_id = offer_dao.create_offer_with_transaction(offer_payload)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Offers",
        action="CREATE",
        record_id=offer_code,
        description=f"Generated offer {offer_code} for {app['first_name']} {app['last_name']} ({pkg} LPA at {app['company_name']})"
    )

    return offer_id


def update_offer_status(offer_id, new_status, remarks=None, user_id=None, user_name=None):
    valid_statuses = ["OFFERED", "ACCEPTED", "REJECTED", "EXPIRED", "WITHDRAWN"]
    if new_status not in valid_statuses:
        raise ValidationError(f"Invalid offer status '{new_status}'. Allowed: {', '.join(valid_statuses)}")

    offer = offer_dao.get_offer_by_id(offer_id)
    if not offer:
        raise NotFoundError(f"Offer #{offer_id} not found.")

    offer_dao.update_offer_status(offer_id, new_status, remarks)

    # If offer rejected or withdrawn, reflect in application if desired
    if new_status in ["REJECTED", "WITHDRAWN"]:
        app_id = offer["application_id"]
        application_dao.update_application_stage(
            application_id=app_id,
            new_stage=new_status,
            remarks=f"Offer was {new_status.lower()}: {remarks or 'No remarks'}",
            user_id=user_id
        )

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Offers",
        action="STATUS_CHANGE",
        record_id=offer.get("offer_code"),
        description=f"Updated offer {offer.get('offer_code')} status to {new_status}"
    )

    return True


def record_placement(data, user_id=None, user_name=None):
    """
    Records a formal placement for an offer and synchronizes joining outcome,
    application stage, and candidate placement status atomically.
    """
    offer_id = data.get("offer_id")
    if not offer_id:
        raise ValidationError("Offer ID is required.")

    offer = offer_dao.get_offer_by_id(offer_id)
    if not offer:
        raise NotFoundError(f"Offer #{offer_id} not found.")

    # Check if placement already exists
    existing = placement_dao.get_placement_by_offer_id(offer_id)
    if existing:
        raise DuplicateError(f"A placement record ({existing['placement_code']}) already exists for offer #{offer_id}.")

    errors = []
    designation = (data.get("designation") or offer["designation"]).strip()
    try:
        final_pkg = float(data.get("final_package_lpa", offer["package_lpa"]))
        if final_pkg <= 0:
            errors.append("Final Package must be greater than zero.")
    except (ValueError, TypeError):
        errors.append("Final package must be a valid number.")

    exp_date = data.get("expected_joining_date") or offer["expected_joining_date"]
    if not exp_date:
        errors.append("Expected Joining Date is required.")

    joining_status = data.get("joining_status", "PENDING")
    valid_joining_statuses = ["PENDING", "JOINED", "NOT_JOINED", "DEFERRED", "NO_SHOW"]
    if joining_status not in valid_joining_statuses:
        errors.append(f"Invalid joining status: '{joining_status}'. Allowed: {', '.join(valid_joining_statuses)}")

    actual_date = data.get("actual_joining_date")
    if joining_status == "JOINED" and not actual_date:
        actual_date = exp_date  # Default to expected date if confirmed joined

    if errors:
        raise ValidationError("; ".join(errors), errors=errors)

    plc_code = generate_placement_code()
    plc_payload = {
        "placement_code": plc_code,
        "offer_id": offer_id,
        "candidate_id": offer["candidate_id"],
        "company_id": offer["company_id"],
        "job_id": offer["job_id"],
        "designation": designation,
        "final_package_lpa": final_pkg,
        "expected_joining_date": exp_date,
        "actual_joining_date": actual_date,
        "joining_status": joining_status,
        "remarks": data.get("remarks"),
        "recorded_by": user_id
    }

    placement_id = placement_dao.record_placement_with_transaction(plc_payload)

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Placements",
        action="RECORD",
        record_id=plc_code,
        description=f"Recorded placement {plc_code} for {offer['first_name']} {offer['last_name']} at {offer['company_name']} ({joining_status})"
    )

    return placement_id


def update_placement_joining_outcome(placement_id, joining_status, actual_joining_date=None,
                                     remarks=None, user_id=None, user_name=None):
    valid_statuses = ["PENDING", "JOINED", "NOT_JOINED", "DEFERRED", "NO_SHOW"]
    if joining_status not in valid_statuses:
        raise ValidationError(f"Invalid joining status '{joining_status}'.")

    placement = placement_dao.get_placement_by_id(placement_id)
    if not placement:
        raise NotFoundError(f"Placement #{placement_id} not found.")

    placement_dao.update_joining_outcome_with_transaction(
        placement_id=placement_id,
        joining_status=joining_status,
        actual_joining_date=actual_joining_date,
        remarks=remarks,
        user_id=user_id
    )

    activity_dao.log_activity(
        user_id=user_id,
        user_name=user_name,
        module="Placements",
        action="JOIN_STATUS_UPDATE",
        record_id=placement.get("placement_code"),
        description=f"Updated placement {placement.get('placement_code')} joining outcome to {joining_status}"
    )

    return True

