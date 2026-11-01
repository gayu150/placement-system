"""
Recruitment & Placement Management System
Candidate Eligibility Evaluation Service
Evaluates candidate against job requirements with detailed explanations.
"""

from datetime import date, datetime
from models.application import EligibilityResult
from dao import candidate_dao, job_dao, application_dao


PROFICIENCY_LEVELS = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
    "expert": 4
}


def _parse_date(val):
    if not val:
        return None
    if isinstance(val, (date, datetime)):
        return val if isinstance(val, date) else val.date()
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def evaluate_eligibility(candidate_id, job_id, check_existing_app=True) -> EligibilityResult:
    """
    Evaluates a candidate's eligibility against an open job.
    Returns EligibilityResult containing is_eligible flag and list of reasons.
    """
    reasons = []
    is_eligible = True

    candidate = candidate_dao.get_candidate_by_id(candidate_id)
    if not candidate:
        return EligibilityResult(is_eligible=False, reasons=[f"Candidate ID #{candidate_id} not found."])

    job = job_dao.get_job_by_id(job_id)
    if not job:
        return EligibilityResult(is_eligible=False, reasons=[f"Job ID #{job_id} not found."])

    # 1. Candidate is active
    if candidate.get("profile_status") != "Active":
        is_eligible = False
        reasons.append("Candidate profile is inactive.")

    # 2. Job is open
    if job.get("status") != "Open":
        is_eligible = False
        reasons.append(f"Job is not open for applications (current status: {job.get('status')}).")

    # Deadline check
    today = date.today()
    job_deadline = _parse_date(job.get("deadline"))
    if job_deadline and job_deadline < today:
        is_eligible = False
        reasons.append(f"Job application deadline ({job_deadline}) has passed.")

    # 3. Duplicate application check
    if check_existing_app:
        existing_app = application_dao.get_application_by_candidate_and_job(candidate_id, job_id)
        if existing_app:
            is_eligible = False
            reasons.append(f"Candidate has already applied for this job (Application: {existing_app['application_code']}, Stage: {existing_app['current_stage']}).")

    # 4. Qualification match
    job_qual_raw = (job.get("qualification_req") or "Any").strip()
    if job_qual_raw.lower() != "any":
        allowed_quals = [q.strip().lower() for q in job_qual_raw.split(",")]
        cand_qual = (candidate.get("qualification") or "").strip().lower()
        if cand_qual not in allowed_quals:
            is_eligible = False
            reasons.append(f"Qualification '{candidate.get('qualification')}' does not match requirement ({job.get('qualification_req')}).")

    # 5. Percentage requirement
    cand_pct = float(candidate.get("percentage") or 0.0)
    min_pct = float(job.get("min_percentage") or 0.0)
    if cand_pct < min_pct:
        is_eligible = False
        reasons.append(f"Academic percentage ({cand_pct}%) is below minimum required ({min_pct}%).")

    # 6. Passing year range
    cand_year = int(candidate.get("passing_year") or 0)
    min_yr = int(job.get("min_passing_year") or 0)
    max_yr = int(job.get("max_passing_year") or 9999)
    if cand_year < min_yr or cand_year > max_yr:
        is_eligible = False
        reasons.append(f"Passing year ({cand_year}) is outside eligible range ({min_yr} - {max_yr}).")

    # 7. Backlogs count
    cand_backlogs = int(candidate.get("backlog_count") or 0)
    max_backlogs = int(job.get("max_backlogs") or 0)
    if cand_backlogs > max_backlogs:
        is_eligible = False
        reasons.append(f"Active backlogs ({cand_backlogs}) exceed maximum allowed ({max_backlogs}).")

    # 8. Technology & Skill requirements
    # Gather candidate skills map: skill_name.lower() -> level
    cand_skills_map = {}
    for cs in candidate.get("skills", []):
        name = cs["skill_name"].strip().lower()
        level = PROFICIENCY_LEVELS.get(cs.get("proficiency_level", "intermediate").lower(), 2)
        cand_skills_map[name] = max(cand_skills_map.get(name, 0), level)

    # Also primary tech
    primary_tech = (candidate.get("primary_technology") or "").strip().lower()
    primary_prof = PROFICIENCY_LEVELS.get(candidate.get("skill_proficiency", "intermediate").lower(), 2)
    if primary_tech:
        cand_skills_map[primary_tech] = max(cand_skills_map.get(primary_tech, 0), primary_prof)

    # Check job required skills
    job_skills = job.get("skills", [])
    for js in job_skills:
        req_name = js["skill_name"].strip().lower()
        is_mandatory = bool(js.get("is_mandatory", 1))
        min_prof_str = js.get("min_proficiency", "intermediate")
        req_level = PROFICIENCY_LEVELS.get(min_prof_str.lower(), 2)

        if is_mandatory:
            cand_level = cand_skills_map.get(req_name)
            if cand_level is None:
                is_eligible = False
                reasons.append(f"Missing mandatory required skill: {js['skill_name']} ({min_prof_str}).")
            elif cand_level < req_level:
                is_eligible = False
                reasons.append(
                    f"Proficiency in {js['skill_name']} is below requirement "
                    f"(Requires at least {min_prof_str})."
                )

    if is_eligible:
        reasons.append("All academic, backlog, qualification, and required skill criteria satisfied.")

    return EligibilityResult(is_eligible=is_eligible, reasons=reasons)
