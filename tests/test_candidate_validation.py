"""
Tests for Candidate Validation & Management Rules
- Percentage bounds (0 - 100)
- Non-negative backlogs
- Unique candidate code, email, mobile
- Soft-deactivation preservation
"""

import pytest
from services import candidate_service, exceptions
from dao import candidate_dao


def test_candidate_valid_creation():
    """Verify valid candidate data is successfully created."""
    cand_data = {
        "candidate_code": "TEST-CAND-001",
        "first_name": "Test",
        "last_name": "User",
        "email": "test.user@university.edu",
        "mobile": "9998887771",
        "qualification": "B.Tech",
        "college": "Testing Engineering College",
        "university": "Test University",
        "passing_year": 2026,
        "percentage": 82.50,
        "cgpa": 8.5,
        "backlog_count": 0,
        "primary_technology": "Python",
        "skill_proficiency": "Intermediate",
        "experience_years": 0.0,
        "current_location": "Bengaluru",
        "preferred_location": "Bengaluru, Hyderabad",
        "profile_status": "Active",
        "placement_status": "Unplaced"
    }

    cand_id = candidate_service.create_candidate(cand_data)
    assert cand_id is not None
    assert cand_id > 0

    fetched = candidate_dao.get_candidate_by_id(cand_id)
    assert fetched["first_name"] == "Test"
    assert fetched["percentage"] == 82.50


def test_candidate_percentage_out_of_bounds():
    """Percentage > 100 or < 0 must be rejected."""
    bad_data_high = {
        "candidate_code": "TEST-CAND-HIGH",
        "first_name": "High",
        "last_name": "Score",
        "email": "high.score@test.edu",
        "mobile": "9998887772",
        "qualification": "B.Tech",
        "college": "Test College",
        "university": "Test Univ",
        "passing_year": 2026,
        "percentage": 105.00,  # Invalid
        "primary_technology": "Python",
        "current_location": "Pune",
        "preferred_location": "Pune"
    }
    with pytest.raises(exceptions.ValidationError) as exc_info:
        candidate_service.create_candidate(bad_data_high)
    assert "Percentage must be between 0.00 and 100.00" in str(exc_info.value)

    bad_data_low = bad_data_high.copy()
    bad_data_low["candidate_code"] = "TEST-CAND-LOW"
    bad_data_low["email"] = "low.score@test.edu"
    bad_data_low["mobile"] = "9998887773"
    bad_data_low["percentage"] = -5.00  # Invalid
    with pytest.raises(exceptions.ValidationError) as exc_info:
        candidate_service.create_candidate(bad_data_low)
    assert "Percentage must be between 0.00 and 100.00" in str(exc_info.value)


def test_candidate_negative_backlog_rejected():
    """Backlog count cannot be negative."""
    bad_data = {
        "candidate_code": "TEST-CAND-NEG-BL",
        "first_name": "Negative",
        "last_name": "Backlog",
        "email": "neg.backlog@test.edu",
        "mobile": "9998887774",
        "qualification": "B.Tech",
        "college": "Test College",
        "university": "Test Univ",
        "passing_year": 2026,
        "percentage": 75.00,
        "backlog_count": -2,  # Invalid
        "primary_technology": "Java",
        "current_location": "Delhi",
        "preferred_location": "Noida"
    }
    with pytest.raises(exceptions.ValidationError) as exc_info:
        candidate_service.create_candidate(bad_data)
    assert "Backlog count cannot be negative" in str(exc_info.value)


def test_soft_deactivation_preserves_records():
    """Deactivating candidate updates profile_status to Inactive without deleting data."""
    cand = candidate_dao.get_candidate_by_code("TEST-CAND-001")
    assert cand is not None

    candidate_service.deactivate_candidate(cand["candidate_id"])
    updated = candidate_dao.get_candidate_by_id(cand["candidate_id"])
    assert updated["profile_status"] == "Inactive"

    # Reactivate
    candidate_service.activate_candidate(cand["candidate_id"])
    reactivated = candidate_dao.get_candidate_by_id(cand["candidate_id"])
    assert reactivated["profile_status"] == "Active"

