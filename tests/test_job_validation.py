"""
Tests for Job Posting Validation & Business Rules
- Openings count > 0
- Min package <= Max package
- Deadline cannot be prior to posted date
- Company must exist and be active
- Job status modification
"""

import pytest
from datetime import date, timedelta
from services import job_service, exceptions
from dao import job_dao


def test_job_valid_creation():
    today = date.today().strftime("%Y-%m-%d")
    deadline = (date.today() + timedelta(days=20)).strftime("%Y-%m-%d")

    job_data = {
        "job_code": "TEST-JOB-001",
        "company_id": 1,
        "title": "Software Test Engineer",
        "employment_type": "Full-time",
        "location": "Bengaluru",
        "openings": 4,
        "min_package": 7.00,
        "max_package": 10.00,
        "qualification_req": "B.Tech, MCA",
        "min_percentage": 70.00,
        "min_passing_year": 2025,
        "max_passing_year": 2026,
        "max_backlogs": 0,
        "experience_req": 0.0,
        "posted_date": today,
        "deadline": deadline,
        "status": "Open"
    }

    job_id = job_service.create_job(job_data)
    assert job_id is not None
    assert job_id > 0

    fetched = job_dao.get_job_by_id(job_id)
    assert fetched["title"] == "Software Test Engineer"
    assert fetched["openings"] == 4


def test_job_zero_or_negative_openings_rejected():
    today = date.today().strftime("%Y-%m-%d")
    deadline = (date.today() + timedelta(days=20)).strftime("%Y-%m-%d")

    bad_data = {
        "job_code": "TEST-JOB-ZERO-OP",
        "company_id": 1,
        "title": "Invalid Job",
        "location": "Mumbai",
        "openings": 0,  # Invalid
        "min_package": 6.00,
        "max_package": 8.00,
        "posted_date": today,
        "deadline": deadline
    }

    with pytest.raises(exceptions.ValidationError) as exc_info:
        job_service.create_job(bad_data)
    assert "Openings count must be greater than zero" in str(exc_info.value)


def test_job_min_package_exceeds_max_package_rejected():
    today = date.today().strftime("%Y-%m-%d")
    deadline = (date.today() + timedelta(days=20)).strftime("%Y-%m-%d")

    bad_data = {
        "job_code": "TEST-JOB-BAD-PKG",
        "company_id": 1,
        "title": "Invalid Package Job",
        "location": "Mumbai",
        "openings": 2,
        "min_package": 12.00,  # Greater than max
        "max_package": 8.00,
        "posted_date": today,
        "deadline": deadline
    }

    with pytest.raises(exceptions.ValidationError) as exc_info:
        job_service.create_job(bad_data)
    assert "Minimum package cannot exceed maximum package" in str(exc_info.value)


def test_job_deadline_before_posted_date_rejected():
    today = date.today()
    past_deadline = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    posted_date = today.strftime("%Y-%m-%d")

    bad_data = {
        "job_code": "TEST-JOB-PAST-DEADLINE",
        "company_id": 1,
        "title": "Invalid Deadline Job",
        "location": "Pune",
        "openings": 2,
        "min_package": 6.00,
        "max_package": 8.00,
        "posted_date": posted_date,
        "deadline": past_deadline  # Invalid
    }

    with pytest.raises(exceptions.ValidationError) as exc_info:
        job_service.create_job(bad_data)
    assert "Deadline cannot be before the posted date" in str(exc_info.value)


def test_job_inactive_company_rejected():
    today = date.today().strftime("%Y-%m-%d")
    deadline = (date.today() + timedelta(days=20)).strftime("%Y-%m-%d")

    # Company 6 is Legacy Soft Technologies (Inactive)
    bad_data = {
        "job_code": "TEST-JOB-INACT-COMP",
        "company_id": 6,
        "title": "Inactive Company Job",
        "location": "Chennai",
        "openings": 2,
        "min_package": 5.00,
        "max_package": 7.00,
        "posted_date": today,
        "deadline": deadline
    }

    with pytest.raises(exceptions.ValidationError) as exc_info:
        job_service.create_job(bad_data)
    assert "Cannot post jobs for inactive company" in str(exc_info.value)

