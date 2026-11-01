"""
Tests for Candidate Eligibility Engine
Verifies academic percentage, passing year, backlogs, qualification, and skill checks.
"""

from services import eligibility_service
from dao import candidate_dao, job_dao


def test_eligible_candidate_passes():
    """Verify an active candidate with qualifying marks and skills passes eligibility."""
    cand_data = {
        "candidate_code": "ELIG-CAND-001",
        "first_name": "Eligible",
        "last_name": "Student",
        "email": "eligible.student@college.edu",
        "mobile": "9887766554",
        "qualification": "B.Tech",
        "college": "Tech College",
        "university": "State University",
        "passing_year": 2026,
        "percentage": 85.00,
        "backlog_count": 0,
        "primary_technology": "Python",
        "skill_proficiency": "Advanced",
        "experience_years": 0.0,
        "current_location": "Bengaluru",
        "preferred_location": "Bengaluru",
        "profile_status": "Active",
        "placement_status": "Unplaced"
    }
    from services import candidate_service
    skill_items = [(1, "Advanced"), (3, "Advanced")]  # Python & SQL
    cand_id = candidate_service.create_candidate(cand_data, skill_items)

    result = eligibility_service.evaluate_eligibility(candidate_id=cand_id, job_id=1)
    assert result.is_eligible is True
    assert result.status == "ELIGIBLE"
    assert "criteria satisfied" in result.formatted_remarks.lower()


def test_criteria_check_without_duplicate_flag():
    """Candidate 1 meets criteria for Job 1 when checking pure eligibility criteria."""
    result = eligibility_service.evaluate_eligibility(candidate_id=1, job_id=1, check_existing_app=False)
    assert result.is_eligible is True
    assert result.status == "ELIGIBLE"


def test_ineligible_due_to_percentage():
    """Candidate with lower percentage than job minimum is marked NOT_ELIGIBLE."""
    # Candidate 5 has 62.5% percentage; Job 1 requires 75%
    result = eligibility_service.evaluate_eligibility(candidate_id=5, job_id=1)
    assert result.is_eligible is False
    assert result.status == "NOT_ELIGIBLE"
    assert any("Academic percentage" in r for r in result.reasons)


def test_ineligible_due_to_backlogs():
    """Candidate with more backlogs than allowed is marked NOT_ELIGIBLE."""
    # Candidate 3 has 1 backlog; Job 1 allows 0 backlogs
    result = eligibility_service.evaluate_eligibility(candidate_id=3, job_id=1)
    assert result.is_eligible is False
    assert any("Active backlogs" in r for r in result.reasons)


def test_ineligible_due_to_inactive_profile():
    """Candidate 8 is Inactive and must be disqualified."""
    result = eligibility_service.evaluate_eligibility(candidate_id=8, job_id=2)
    assert result.is_eligible is False
    assert any("inactive" in r.lower() for r in result.reasons)


def test_ineligible_due_to_missing_skills():
    """Job 4 requires Python and Data Analysis; candidate without Data Analysis fails."""
    # Candidate 5 is Java beginner
    result = eligibility_service.evaluate_eligibility(candidate_id=5, job_id=4)
    assert result.is_eligible is False
    assert any("Missing mandatory required skill" in r for r in result.reasons)


def test_ineligible_due_to_closed_job():
    """Job 5 is Closed and must reject eligibility."""
    result = eligibility_service.evaluate_eligibility(candidate_id=1, job_id=5)
    assert result.is_eligible is False
    assert any("Job is not open" in r for r in result.reasons)
