"""
Integration tests for Web Interface, Navigation, and Role Permissions
"""

import pytest


def login_as(client, username="admin", password="Demo@123"):
    return client.post("/login", data={
        "username": username,
        "password": password
    }, follow_redirects=True)


def test_login_flow(client):
    """Test user login and session establishment."""
    res = login_as(client, "admin", "Demo@123")
    assert res.status_code == 200
    assert b"Dashboard" in res.data or b"Dashboard Overview" in res.data


def test_dashboard_renders_metrics(client):
    """Dashboard must render live metrics and cards."""
    login_as(client, "admin", "Demo@123")
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert b"Total Candidates" in res.data
    assert b"Registered Companies" in res.data
    assert b"Open Job Drives" in res.data


def test_candidate_screens(client):
    login_as(client, "admin", "Demo@123")

    # List
    res = client.get("/candidates")
    assert res.status_code == 200
    assert b"Candidate Management" in res.data

    # Detail
    res = client.get("/candidates/1")
    assert res.status_code == 200
    assert b"Aarav" in res.data

    # New
    res = client.get("/candidates/new")
    assert res.status_code == 200
    assert b"Candidate Details Form" in res.data


def test_company_screens(client):
    login_as(client, "admin", "Demo@123")

    # List
    res = client.get("/companies")
    assert res.status_code == 200
    assert b"TechNova Solutions" in res.data

    # Detail
    res = client.get("/companies/1")
    assert res.status_code == 200
    assert b"Company Information" in res.data


def test_job_screens(client):
    login_as(client, "admin", "Demo@123")

    # List
    res = client.get("/jobs")
    assert res.status_code == 200
    assert b"Associate Python Backend Engineer" in res.data

    # Detail
    res = client.get("/jobs/1")
    assert res.status_code == 200
    assert b"Eligibility Requirements" in res.data


def test_application_screens(client):
    login_as(client, "admin", "Demo@123")

    # List
    res = client.get("/applications")
    assert res.status_code == 200
    assert b"Application Management" in res.data

    # Detail
    res = client.get("/applications/1")
    assert res.status_code == 200
    assert b"Application History Timeline" in res.data


def test_interview_and_feedback_screens(client):
    login_as(client, "admin", "Demo@123")

    # List
    res = client.get("/interviews")
    assert res.status_code == 200
    assert b"Interviews & Feedback" in res.data

    # Feedback screen for interview 3 (which is scheduled without feedback yet)
    res = client.get("/interviews/3/feedback")
    assert res.status_code == 200
    assert b"Interviewer Assessment & Ratings Form" in res.data


def test_offer_and_placement_screens(client):
    login_as(client, "admin", "Demo@123")

    # Offers List
    res = client.get("/offers")
    assert res.status_code == 200
    assert b"Job Offers Management" in res.data

    # Placements List
    res = client.get("/placements")
    assert res.status_code == 200
    assert b"Placements & Joining Outcomes" in res.data


def test_reports_hub(client):
    login_as(client, "admin", "Demo@123")
    res = client.get("/reports")
    assert res.status_code == 200
    assert b"Placement & Recruitment Reports" in res.data
    assert b"Recruitment Funnel & Progression Audit" in res.data
    assert b"Candidates by Technology" in res.data
    assert b"Company-Wise Placement Outcomes" in res.data


def test_activity_logs(client):
    login_as(client, "admin", "Demo@123")
    res = client.get("/activity-logs")
    assert res.status_code == 200
    assert b"System Activity Audit Trail" in res.data


def test_unauthenticated_redirect(client):
    """Unauthenticated users attempting to access dashboard should be redirected to login."""
    client.get("/logout")
    res = client.get("/dashboard")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]

