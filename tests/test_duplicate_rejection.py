"""
Tests for Duplicate Rejection Constraints
Verifies that unique candidates and unique applications are strictly enforced
by both application logic and database unique constraints.
"""

import pytest
from services import candidate_service, application_service, exceptions


def test_duplicate_candidate_email_rejected():
    """Registering candidate with existing email must be rejected."""
    dup_email_cand = {
        "candidate_code": "CAND-UNIQUE-991",
        "first_name": "Unique",
        "last_name": "Person",
        "email": "aarav.sharma@student.edu",  # Already taken by Candidate 1
        "mobile": "9991112233",
        "qualification": "B.Tech",
        "college": "Test College",
        "university": "Test Univ",
        "passing_year": 2026,
        "percentage": 78.00,
        "primary_technology": "Python",
        "current_location": "Bengaluru",
        "preferred_location": "Bengaluru"
    }

    with pytest.raises(exceptions.ValidationError) as exc_info:
        candidate_service.create_candidate(dup_email_cand)
    assert "already registered with another candidate" in str(exc_info.value)


def test_duplicate_candidate_mobile_rejected():
    """Registering candidate with existing mobile must be rejected."""
    dup_mobile_cand = {
        "candidate_code": "CAND-UNIQUE-992",
        "first_name": "Unique",
        "last_name": "Person",
        "email": "new.unique.email@test.edu",
        "mobile": "9123456701",  # Already taken by Candidate 1
        "qualification": "B.Tech",
        "college": "Test College",
        "university": "Test Univ",
        "passing_year": 2026,
        "percentage": 78.00,
        "primary_technology": "Python",
        "current_location": "Bengaluru",
        "preferred_location": "Bengaluru"
    }

    with pytest.raises(exceptions.ValidationError) as exc_info:
        candidate_service.create_candidate(dup_mobile_cand)
    assert "already in use by another candidate" in str(exc_info.value)


def test_duplicate_application_rejected():
    """Candidate cannot apply twice for the exact same job drive."""
    # Candidate 1 has already applied for Job 1 in seed data (App 1)
    with pytest.raises(exceptions.DuplicateError) as exc_info:
        application_service.submit_application(candidate_id=1, job_id=1)
    assert "already applied for job" in str(exc_info.value)

