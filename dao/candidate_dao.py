"""
Recruitment & Placement Management System
Candidate Data Access Object
"""

from dao.db import execute_query, execute_one, execute_insert, execute_update, db_transaction


def get_candidate_by_id(candidate_id):
    sql = """
        SELECT * FROM candidates WHERE candidate_id = %s
    """
    candidate = execute_one(sql, (candidate_id,))
    if candidate:
        candidate["skills"] = get_candidate_skills(candidate_id)
    return candidate


def get_candidate_by_code(code):
    sql = "SELECT * FROM candidates WHERE candidate_code = %s"
    candidate = execute_one(sql, (code,))
    if candidate:
        candidate["skills"] = get_candidate_skills(candidate["candidate_id"])
    return candidate


def get_candidate_by_email(email):
    sql = "SELECT * FROM candidates WHERE email = %s"
    return execute_one(sql, (email,))


def get_candidate_by_mobile(mobile):
    sql = "SELECT * FROM candidates WHERE mobile = %s"
    return execute_one(sql, (mobile,))


def get_candidate_skills(candidate_id):
    sql = """
        SELECT cs.id, cs.skill_id, s.skill_name, s.category, cs.proficiency_level
        FROM candidate_skills cs
        JOIN skills s ON cs.skill_id = s.skill_id
        WHERE cs.candidate_id = %s
        ORDER BY s.skill_name ASC
    """
    return execute_query(sql, (candidate_id,))


def get_all_skills():
    sql = "SELECT skill_id, skill_name, category FROM skills ORDER BY category, skill_name ASC"
    return execute_query(sql)


def search_candidates(search=None, technology=None, qualification=None,
                      passing_year=None, profile_status=None, placement_status=None):
    sql = """
        SELECT candidate_id, candidate_code, first_name, last_name, email, mobile,
               qualification, college, university, passing_year, percentage, cgpa,
               backlog_count, primary_technology, skill_proficiency, experience_years,
               current_location, preferred_location, profile_status, placement_status,
               created_at
        FROM candidates
        WHERE 1=1
    """
    params = []

    if search:
        search_pattern = f"%{search.strip()}%"
        sql += """ AND (
            candidate_code LIKE %s OR
            first_name LIKE %s OR
            last_name LIKE %s OR
            email LIKE %s OR
            mobile LIKE %s OR
            college LIKE %s
        )"""
        params.extend([search_pattern] * 6)

    if technology:
        sql += " AND primary_technology = %s"
        params.append(technology.strip())

    if qualification:
        sql += " AND qualification = %s"
        params.append(qualification.strip())

    if passing_year:
        sql += " AND passing_year = %s"
        params.append(int(passing_year))

    if profile_status:
        sql += " AND profile_status = %s"
        params.append(profile_status.strip())

    if placement_status:
        sql += " AND placement_status = %s"
        params.append(placement_status.strip())

    sql += " ORDER BY candidate_id DESC"
    return execute_query(sql, tuple(params) if params else None)


def has_recruitment_history(candidate_id):
    """Checks whether the candidate has any applications, interviews, offers, or placements."""
    sql = "SELECT COUNT(*) as count FROM applications WHERE candidate_id = %s"
    res = execute_one(sql, (candidate_id,))
    return res and res["count"] > 0


def create_candidate(cand_data, skill_items=None):
    """
    Creates a candidate record and their skill associations inside a transaction.
    skill_items: list of tuples (skill_id, proficiency_level)
    """
    with db_transaction() as tx:
        sql = """
            INSERT INTO candidates (
                candidate_code, first_name, last_name, email, mobile,
                date_of_birth, gender, qualification, college, university,
                passing_year, percentage, cgpa, backlog_count, primary_technology,
                skill_proficiency, experience_years, current_location,
                preferred_location, profile_status, placement_status
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s
            )
        """
        params = (
            cand_data["candidate_code"], cand_data["first_name"], cand_data["last_name"],
            cand_data["email"], cand_data["mobile"], cand_data.get("date_of_birth") or None,
            cand_data.get("gender") or None, cand_data["qualification"], cand_data["college"],
            cand_data["university"], cand_data["passing_year"], cand_data["percentage"],
            cand_data.get("cgpa") or None, cand_data.get("backlog_count", 0),
            cand_data["primary_technology"], cand_data.get("skill_proficiency", "Intermediate"),
            cand_data.get("experience_years", 0.0), cand_data["current_location"],
            cand_data["preferred_location"], cand_data.get("profile_status", "Active"),
            cand_data.get("placement_status", "Unplaced")
        )
        tx.execute(sql, params)
        candidate_id = tx.lastrowid

        if skill_items:
            for skill_id, prof in skill_items:
                tx.execute(
                    "INSERT INTO candidate_skills (candidate_id, skill_id, proficiency_level) VALUES (%s, %s, %s)",
                    (candidate_id, skill_id, prof)
                )

        return candidate_id


def update_candidate(candidate_id, cand_data, skill_items=None):
    """Updates candidate and refreshed skill associations in a transaction."""
    with db_transaction() as tx:
        sql = """
            UPDATE candidates SET
                first_name = %s,
                last_name = %s,
                email = %s,
                mobile = %s,
                date_of_birth = %s,
                gender = %s,
                qualification = %s,
                college = %s,
                university = %s,
                passing_year = %s,
                percentage = %s,
                cgpa = %s,
                backlog_count = %s,
                primary_technology = %s,
                skill_proficiency = %s,
                experience_years = %s,
                current_location = %s,
                preferred_location = %s,
                profile_status = %s,
                placement_status = %s
            WHERE candidate_id = %s
        """
        params = (
            cand_data["first_name"], cand_data["last_name"], cand_data["email"],
            cand_data["mobile"], cand_data.get("date_of_birth") or None,
            cand_data.get("gender") or None, cand_data["qualification"], cand_data["college"],
            cand_data["university"], cand_data["passing_year"], cand_data["percentage"],
            cand_data.get("cgpa") or None, cand_data.get("backlog_count", 0),
            cand_data["primary_technology"], cand_data.get("skill_proficiency", "Intermediate"),
            cand_data.get("experience_years", 0.0), cand_data["current_location"],
            cand_data["preferred_location"], cand_data.get("profile_status", "Active"),
            cand_data.get("placement_status", "Unplaced"), candidate_id
        )
        tx.execute(sql, params)

        if skill_items is not None:
            tx.execute("DELETE FROM candidate_skills WHERE candidate_id = %s", (candidate_id,))
            for skill_id, prof in skill_items:
                tx.execute(
                    "INSERT INTO candidate_skills (candidate_id, skill_id, proficiency_level) VALUES (%s, %s, %s)",
                    (candidate_id, skill_id, prof)
                )

        return True


def set_candidate_status(candidate_id, status):
    sql = "UPDATE candidates SET profile_status = %s WHERE candidate_id = %s"
    return execute_update(sql, (status, candidate_id))


def set_candidate_placement_status(candidate_id, placement_status):
    sql = "UPDATE candidates SET placement_status = %s WHERE candidate_id = %s"
    return execute_update(sql, (placement_status, candidate_id))


def get_candidate_applications(candidate_id):
    sql = """
        SELECT a.application_id, a.application_code, a.applied_date, a.current_stage,
               a.eligibility_status, j.job_id, j.job_code, j.title AS job_title,
               c.company_name, c.company_id
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        WHERE a.candidate_id = %s
        ORDER BY a.application_id DESC
    """
    return execute_query(sql, (candidate_id,))

