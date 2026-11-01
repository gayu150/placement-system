"""
Recruitment & Placement Management System
Job Openings Data Access Object
"""

from dao.db import execute_query, execute_one, execute_insert, execute_update, db_transaction


def get_job_by_id(job_id):
    sql = """
        SELECT j.*, c.company_name, c.company_code, c.location AS company_location,
               c.industry AS company_industry, c.hr_name, c.hr_email,
               u.full_name AS created_by_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        LEFT JOIN users u ON j.created_by = u.user_id
        WHERE j.job_id = %s
    """
    job = execute_one(sql, (job_id,))
    if job:
        job["skills"] = get_job_skills(job_id)
    return job


def get_job_by_code(code):
    sql = """
        SELECT j.*, c.company_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        WHERE j.job_code = %s
    """
    job = execute_one(sql, (code,))
    if job:
        job["skills"] = get_job_skills(job["job_id"])
    return job


def get_job_skills(job_id):
    sql = """
        SELECT js.id, js.skill_id, s.skill_name, s.category,
               js.is_mandatory, js.min_proficiency
        FROM job_skills js
        JOIN skills s ON js.skill_id = s.skill_id
        WHERE js.job_id = %s
        ORDER BY js.is_mandatory DESC, s.skill_name ASC
    """
    return execute_query(sql, (job_id,))


def search_jobs(search=None, company_id=None, status=None, employment_type=None):
    sql = """
        SELECT j.job_id, j.job_code, j.company_id, j.title, j.employment_type,
               j.location, j.openings, j.min_package, j.max_package,
               j.qualification_req, j.min_percentage, j.min_passing_year,
               j.max_passing_year, j.max_backlogs, j.experience_req,
               j.posted_date, j.deadline, j.status,
               c.company_name, c.company_code,
               (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS total_applications
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        WHERE 1=1
    """
    params = []

    if search:
        search_pattern = f"%{search.strip()}%"
        sql += """ AND (
            j.job_code LIKE %s OR
            j.title LIKE %s OR
            j.location LIKE %s OR
            c.company_name LIKE %s
        )"""
        params.extend([search_pattern] * 4)

    if company_id:
        sql += " AND j.company_id = %s"
        params.append(int(company_id))

    if status:
        sql += " AND j.status = %s"
        params.append(status.strip())

    if employment_type:
        sql += " AND j.employment_type = %s"
        params.append(employment_type.strip())

    sql += " ORDER BY j.job_id DESC"
    return execute_query(sql, tuple(params) if params else None)


def get_open_jobs():
    """Return all jobs that are currently open."""
    sql = """
        SELECT j.job_id, j.job_code, j.title, j.location, j.openings,
               j.min_package, j.max_package, j.qualification_req,
               j.min_percentage, j.min_passing_year, j.max_passing_year,
               j.max_backlogs, j.posted_date, j.deadline,
               c.company_id, c.company_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        WHERE j.status = 'Open'
        ORDER BY j.job_id DESC
    """
    return execute_query(sql)


def has_applications(job_id):
    sql = "SELECT COUNT(*) AS count FROM applications WHERE job_id = %s"
    res = execute_one(sql, (job_id,))
    return res and res["count"] > 0


def create_job(job_data, skill_requirements=None):
    """
    Creates a new job posting with skill requirements in a single transaction.
    skill_requirements: list of tuples (skill_id, is_mandatory, min_proficiency)
    """
    with db_transaction() as tx:
        sql = """
            INSERT INTO jobs (
                job_code, company_id, title, employment_type, location,
                openings, min_package, max_package, qualification_req,
                min_percentage, min_passing_year, max_passing_year,
                max_backlogs, experience_req, posted_date, deadline,
                status, created_by
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            )
        """
        params = (
            job_data["job_code"], job_data["company_id"], job_data["title"],
            job_data.get("employment_type", "Full-time"), job_data["location"],
            job_data["openings"], job_data["min_package"], job_data["max_package"],
            job_data.get("qualification_req", "Any"), job_data.get("min_percentage", 60.0),
            job_data["min_passing_year"], job_data["max_passing_year"],
            job_data.get("max_backlogs", 0), job_data.get("experience_req", 0.0),
            job_data["posted_date"], job_data["deadline"],
            job_data.get("status", "Open"), job_data.get("created_by")
        )
        tx.execute(sql, params)
        job_id = tx.lastrowid

        if skill_requirements:
            for skill_id, is_mand, min_prof in skill_requirements:
                tx.execute(
                    """INSERT INTO job_skills (job_id, skill_id, is_mandatory, min_proficiency)
                       VALUES (%s, %s, %s, %s)""",
                    (job_id, skill_id, is_mand, min_prof)
                )

        return job_id


def update_job(job_id, job_data, skill_requirements=None):
    """Updates an existing job and refreshes skill requirements in a transaction."""
    with db_transaction() as tx:
        sql = """
            UPDATE jobs SET
                company_id = %s,
                title = %s,
                employment_type = %s,
                location = %s,
                openings = %s,
                min_package = %s,
                max_package = %s,
                qualification_req = %s,
                min_percentage = %s,
                min_passing_year = %s,
                max_passing_year = %s,
                max_backlogs = %s,
                experience_req = %s,
                posted_date = %s,
                deadline = %s,
                status = %s
            WHERE job_id = %s
        """
        params = (
            job_data["company_id"], job_data["title"],
            job_data.get("employment_type", "Full-time"), job_data["location"],
            job_data["openings"], job_data["min_package"], job_data["max_package"],
            job_data.get("qualification_req", "Any"), job_data.get("min_percentage", 60.0),
            job_data["min_passing_year"], job_data["max_passing_year"],
            job_data.get("max_backlogs", 0), job_data.get("experience_req", 0.0),
            job_data["posted_date"], job_data["deadline"],
            job_data.get("status", "Open"), job_id
        )
        tx.execute(sql, params)

        if skill_requirements is not None:
            tx.execute("DELETE FROM job_skills WHERE job_id = %s", (job_id,))
            for skill_id, is_mand, min_prof in skill_requirements:
                tx.execute(
                    """INSERT INTO job_skills (job_id, skill_id, is_mandatory, min_proficiency)
                       VALUES (%s, %s, %s, %s)""",
                    (job_id, skill_id, is_mand, min_prof)
                )

        return True


def update_job_status(job_id, status):
    sql = "UPDATE jobs SET status = %s WHERE job_id = %s"
    return execute_update(sql, (status, job_id))

