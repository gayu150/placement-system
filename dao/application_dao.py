"""
Recruitment & Placement Management System
Application & Stage History Data Access Object
"""

from dao.db import execute_query, execute_one, execute_insert, execute_update, db_transaction


def get_application_by_id(application_id):
    sql = """
        SELECT a.*,
               c.candidate_code, c.first_name, c.last_name, c.email AS candidate_email,
               c.mobile AS candidate_mobile, c.qualification, c.percentage,
               c.passing_year, c.backlog_count, c.primary_technology,
               j.job_code, j.title AS job_title, j.location AS job_location,
               j.min_package, j.max_package, j.status AS job_status,
               comp.company_id, comp.company_name, comp.company_code,
               u.full_name AS override_by_name
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies comp ON j.company_id = comp.company_id
        LEFT JOIN users u ON a.override_by = u.user_id
        WHERE a.application_id = %s
    """
    return execute_one(sql, (application_id,))


def get_application_by_code(code):
    sql = """
        SELECT a.*,
               c.candidate_code, c.first_name, c.last_name,
               j.job_code, j.title AS job_title,
               comp.company_name
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies comp ON j.company_id = comp.company_id
        WHERE a.application_code = %s
    """
    return execute_one(sql, (code,))


def get_application_by_candidate_and_job(candidate_id, job_id):
    sql = """
        SELECT * FROM applications
        WHERE candidate_id = %s AND job_id = %s
    """
    return execute_one(sql, (candidate_id, job_id))


def search_applications(search=None, job_id=None, candidate_id=None, stage=None, eligibility=None):
    sql = """
        SELECT a.application_id, a.application_code, a.applied_date, a.current_stage,
               a.eligibility_status, a.is_override,
               c.candidate_id, c.candidate_code, c.first_name, c.last_name,
               c.email AS candidate_email, c.primary_technology,
               j.job_id, j.job_code, j.title AS job_title,
               comp.company_id, comp.company_name
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies comp ON j.company_id = comp.company_id
        WHERE 1=1
    """
    params = []

    if search:
        search_pattern = f"%{search.strip()}%"
        sql += """ AND (
            a.application_code LIKE %s OR
            c.candidate_code LIKE %s OR
            c.first_name LIKE %s OR
            c.last_name LIKE %s OR
            j.title LIKE %s OR
            comp.company_name LIKE %s
        )"""
        params.extend([search_pattern] * 6)

    if job_id:
        sql += " AND a.job_id = %s"
        params.append(int(job_id))

    if candidate_id:
        sql += " AND a.candidate_id = %s"
        params.append(int(candidate_id))

    if stage:
        sql += " AND a.current_stage = %s"
        params.append(stage.strip())

    if eligibility:
        sql += " AND a.eligibility_status = %s"
        params.append(eligibility.strip())

    sql += " ORDER BY a.application_id DESC"
    return execute_query(sql, tuple(params) if params else None)


def create_application(app_data, user_id=None, initial_remarks="Application submitted."):
    """
    Creates an application and logs its initial stage in application_history.
    Executed inside a transaction.
    """
    with db_transaction() as tx:
        sql = """
            INSERT INTO applications (
                application_code, candidate_id, job_id, current_stage,
                eligibility_status, eligibility_remarks, is_override,
                override_reason, override_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            app_data["application_code"], app_data["candidate_id"], app_data["job_id"],
            app_data.get("current_stage", "APPLIED"),
            app_data["eligibility_status"],
            app_data.get("eligibility_remarks"),
            app_data.get("is_override", 0),
            app_data.get("override_reason"),
            app_data.get("override_by")
        )
        tx.execute(sql, params)
        app_id = tx.lastrowid

        # Insert first stage history
        hist_sql = """
            INSERT INTO application_history (application_id, old_stage, new_stage, remarks, changed_by)
            VALUES (%s, %s, %s, %s, %s)
        """
        tx.execute(hist_sql, (app_id, "NONE", app_data.get("current_stage", "APPLIED"), initial_remarks, user_id))

        return app_id


def update_application_stage(application_id, new_stage, remarks=None, user_id=None):
    """
    Updates application current stage and logs history in a transaction.
    """
    with db_transaction() as tx:
        # Fetch current stage
        tx.execute("SELECT current_stage FROM applications WHERE application_id = %s", (application_id,))
        row = tx.fetchone()
        if not row:
            raise ValueError(f"Application #{application_id} not found.")

        old_stage = row["current_stage"]

        # Update stage
        tx.execute(
            "UPDATE applications SET current_stage = %s WHERE application_id = %s",
            (new_stage, application_id)
        )

        # Log history
        tx.execute(
            """INSERT INTO application_history (application_id, old_stage, new_stage, remarks, changed_by)
               VALUES (%s, %s, %s, %s, %s)""",
            (application_id, old_stage, new_stage, remarks or f"Stage updated to {new_stage}", user_id)
        )

        return True


def get_application_history(application_id):
    sql = """
        SELECT h.history_id, h.application_id, h.old_stage, h.new_stage,
               h.remarks, h.changed_at, u.full_name AS changed_by_name
        FROM application_history h
        LEFT JOIN users u ON h.changed_by = u.user_id
        WHERE h.application_id = %s
        ORDER BY h.history_id ASC
    """
    return execute_query(sql, (application_id,))

