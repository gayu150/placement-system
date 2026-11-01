"""
Tests for Offer and Placement Workflows
Verifies transactional offer generation, acceptance, joining, and multi-record synchronization.
"""

import pytest
from services import offer_service, application_service, exceptions
from dao import offer_dao, placement_dao, application_dao, candidate_dao


def test_offer_creation_and_transactional_sync():
    """Generating offer updates application stage to OFFERED in a single transaction."""
    # App 4 (Ananya, Job 4) is in SELECTED stage
    app = application_dao.get_application_by_id(4)
    assert app["current_stage"] == "SELECTED"

    # App 4 already has offer 3 in seed data; let's check App 6 (Aditya, Job 3)
    # Transition App 6 from INTERVIEWED to SELECTED
    application_service.transition_stage(6, "SELECTED")
    app6 = application_dao.get_application_by_id(6)
    assert app6["current_stage"] == "SELECTED"

    offer_data = {
        "application_id": 6,
        "designation": "Associate Fintech Engineer",
        "package_lpa": 10.50,
        "offer_date": "2026-03-01",
        "expected_joining_date": "2026-03-20",
        "remarks": "Standard terms with laptop allowance."
    }

    offer_id = offer_service.create_offer(offer_data)
    assert offer_id is not None

    # Verify application stage was atomically transitioned to OFFERED
    updated_app = application_dao.get_application_by_id(6)
    assert updated_app["current_stage"] == "OFFERED"

    # Verify history entry
    hist = application_dao.get_application_history(6)
    assert hist[-1]["new_stage"] == "OFFERED"


def test_duplicate_offer_rejected():
    """Cannot create more than one offer for the same application."""
    # App 1 already has Offer 1
    offer_data = {
        "application_id": 1,
        "designation": "Duplicate Offer",
        "package_lpa": 9.00,
        "offer_date": "2026-03-05",
        "expected_joining_date": "2026-03-25"
    }

    with pytest.raises(Exception):
        offer_service.create_offer(offer_data)


def test_placement_joining_synchronization():
    """Confirming candidate joining updates placement, application stage, and candidate status."""
    # Offer 3 was issued for App 4 (Candidate 4, Ananya)
    offer = offer_dao.get_offer_by_id(3)
    assert offer is not None

    placement_data = {
        "offer_id": 3,
        "designation": "Junior Data & ML Analyst",
        "final_package_lpa": 9.50,
        "expected_joining_date": "2026-07-01",
        "actual_joining_date": "2026-07-01",
        "joining_status": "JOINED",
        "remarks": "Candidate completed induction successfully."
    }

    plc_id = offer_service.record_placement(placement_data)
    assert plc_id is not None

    # Verify Application 4 is now JOINED
    app4 = application_dao.get_application_by_id(4)
    assert app4["current_stage"] == "JOINED"

    # Verify Candidate 4 placement status is now Placed
    cand4 = candidate_dao.get_candidate_by_id(4)
    assert cand4["placement_status"] == "Placed"

    # Verify duplicate placement for same offer is rejected
    with pytest.raises(exceptions.DuplicateError):
        offer_service.record_placement(placement_data)

