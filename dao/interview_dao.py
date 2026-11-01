"""
Recruitment & Placement Management System
Interview Rounds & Feedback Data Access Object
"""

from dao.db import execute_query, execute_one, execute_insert, execute_update, db_transaction


def get_interview_by_id(interview_id):
    sql = """
        SELECT ir.*,
               a.application_code, a.candidate_id, a.job_id, a.current_stage,
               c.first_name, c.last_name, c.candidate_code, c.email AS candidate_email,
               j.title AS job_title, comp.company_name,
               u.full_name AS scheduled_by_name
        FROM interview_rounds ir
        JOIN applications a ON ir.application_id = a.application_id
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies comp ON j.company_id = comp.company_id
        LEFT JOIN users u ON ir.scheduled_by = u.user_id
        WHERE ir.interview_id = %s
    """
    interview = execute_one(sql, (interview_id,))
    if interview:
        interview["feedback"] = get_feedback_by_interview_id(interview_id)
    return interview


def get_interviews_by_application(application_id):
    sql = """
        SELECT ir.*,
               fb.feedback_id, fb.technical_rating, fb.communication_rating,
               fb.problem_solving_rating, fb.overall_rating, fb.recommendation,
               fb.remarks AS feedback_remarks, fb.submitted_at
        FROM interview_rounds ir
        LEFT JOIN interview_feedback fb ON ir.interview_id = fb.interview_id
        WHERE ir.application_id = %s
        ORDER BY ir.round_number ASC
    """
    return execute_query(sql, (application_id,))


def search_interviews(search=None, status=None, date_from=None, date_to=None):
    sql = """
        SELECT ir.interview_id, ir.application_id, ir.round_number, ir.round_name,
               ir.scheduled_date, ir.scheduled_time, ir.interview_mode,
               ir.interviewer_name, ir.meeting_link_or_venue, ir.status,
               a.application_code, a.candidate_id, c.candidate_code, c.first_name, c.last_name,
               j.title AS job_title, comp.company_name,
               fb.feedback_id, fb.overall_rating, fb.recommendation
        FROM interview_rounds ir
        JOIN applications a ON ir.application_id = a.application_id
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies comp ON j.company_id = comp.company_id
        LEFT JOIN interview_feedback fb ON ir.interview_id = fb.interview_id
        WHERE 1=1
    """
    params = []

    if search:
        search_pattern = f"%{search.strip()}%"
        sql += """ AND (
            c.first_name LIKE %s OR
            c.last_name LIKE %s OR
            c.candidate_code LIKE %s OR
            j.title LIKE %s OR
            comp.company_name LIKE %s OR
            ir.interviewer_name LIKE %s
        )"""
        params.extend([search_pattern] * 6)

    if status:
        sql += " AND ir.status = %s"
        params.append(status.strip())

    if date_from:
        sql += " AND ir.scheduled_date >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND ir.scheduled_date <= %s"
        params.append(date_to)

    sql += " ORDER BY ir.scheduled_date DESC, ir.scheduled_time DESC"
    return execute_query(sql, tuple(params) if params else None)


def schedule_interview(interview_data):
    """
    Schedules an interview round and transitions the application stage to INTERVIEW_SCHEDULED
    if it is not already in an active interview stage.
    """
    with db_transaction() as tx:
        sql = """
            INSERT INTO interview_rounds (
                application_id, round_number, round_name, scheduled_date,
                scheduled_time, interview_mode, interviewer_name,
                meeting_link_or_venue, status, scheduled_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            interview_data["application_id"], interview_data["round_number"],
            interview_data["round_name"], interview_data["scheduled_date"],
            interview_data["scheduled_time"], interview_data.get("interview_mode", "Online"),
            interview_data["interviewer_name"], interview_data["meeting_link_or_venue"],
            interview_data.get("status", "SCHEDULED"), interview_data.get("scheduled_by")
        )
        tx.execute(sql, params)
        interview_id = tx.lastrowid

        # Update application stage to INTERVIEW_SCHEDULED if shortlisted
        app_id = interview_data["application_id"]
        tx.execute("SELECT current_stage FROM applications WHERE application_id = %s", (app_id,))
        app_row = tx.fetchone()
        if app_row and app_row["current_stage"] in ["SHORTLISTED", "INTERVIEWED"]:
            tx.execute("UPDATE applications SET current_stage = 'INTERVIEW_SCHEDULED' WHERE application_id = %s", (app_id,))
            tx.execute(
                """INSERT INTO application_history (application_id, old_stage, new_stage, remarks, changed_by)
                   VALUES (%s, %s, 'INTERVIEW_SCHEDULED', %s, %s)""",
                (app_id, app_row["current_stage"],
                 f"Interview Round #{interview_data['round_number']} ({interview_data['round_name']}) scheduled.",
                 interview_data.get("scheduled_by"))
            )

        return interview_id


def update_interview_status(interview_id, status):
    sql = "UPDATE interview_rounds SET status = %s WHERE interview_id = %s"
    return execute_update(sql, (status, interview_id))


def reschedule_interview(interview_id, new_date, new_time, link_or_venue=None):
    if link_or_venue:
        sql = """
            UPDATE interview_rounds
            SET scheduled_date = %s, scheduled_time = %s,
                meeting_link_or_venue = %s, status = 'RESCHEDULED'
            WHERE interview_id = %s
        """
        return execute_update(sql, (new_date, new_time, link_or_venue, interview_id))
    else:
        sql = """
            UPDATE interview_rounds
            SET scheduled_date = %s, scheduled_time = %s, status = 'RESCHEDULED'
            WHERE interview_id = %s
        """
        return execute_update(sql, (new_date, new_time, interview_id))


def get_feedback_by_interview_id(interview_id):
    sql = """
        SELECT fb.*, u.full_name AS submitted_by_name
        FROM interview_feedback fb
        LEFT JOIN users u ON fb.submitted_by = u.user_id
        WHERE fb.interview_id = %s
    """
    return execute_one(sql, (interview_id,))


def record_feedback(feedback_data):
    """
    Records interview feedback and updates round status to COMPLETED.
    Optionally promotes application based on recommendation in a transaction.
    """
    with db_transaction() as tx:
        # Check if feedback already exists
        interview_id = feedback_data["interview_id"]
        tx.execute("SELECT feedback_id FROM interview_feedback WHERE interview_id = %s", (interview_id,))
        if tx.fetchone():
            raise ValueError(f"Feedback has already been recorded for interview round #{interview_id}.")

        sql = """
            INSERT INTO interview_feedback (
                interview_id, technical_rating, communication_rating,
                problem_solving_rating, overall_rating, recommendation,
                remarks, submitted_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            interview_id, feedback_data["technical_rating"],
            feedback_data["communication_rating"], feedback_data["problem_solving_rating"],
            feedback_data["overall_rating"], feedback_data["recommendation"],
            feedback_data["remarks"], feedback_data.get("submitted_by")
        )
        tx.execute(sql, params)
        feedback_id = tx.lastrowid

        # Mark interview round as COMPLETED
        tx.execute("UPDATE interview_rounds SET status = 'COMPLETED' WHERE interview_id = %s", (interview_id,))

        # Update application stage
        tx.execute("""
            SELECT ir.application_id, a.current_stage
            FROM interview_rounds ir
            JOIN applications a ON ir.application_id = a.application_id
            WHERE ir.interview_id = %s
        """, (interview_id,))
        app_info = tx.fetchone()

        if app_info:
            app_id = app_info["application_id"]
            current_stage = app_info["current_stage"]
            recom = feedback_data["recommendation"]

            new_stage = None
            if recom == "SELECTED":
                new_stage = "SELECTED"
            elif recom == "REJECTED":
                new_stage = "REJECTED"
            else:
                # NEXT_ROUND or ON_HOLD
                new_stage = "INTERVIEWED"

            if new_stage and new_stage != current_stage:
                tx.execute("UPDATE applications SET current_stage = %s WHERE application_id = %s", (new_stage, app_id))
                tx.execute(
                    """INSERT INTO application_history (application_id, old_stage, new_stage, remarks, changed_by)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (app_id, current_stage, new_stage,
                     f"Interview feedback submitted ({recom}): {feedback_data['remarks'][:100]}",
                     feedback_data.get("submitted_by"))
                )

        return feedback_id
