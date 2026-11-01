"""
Recruitment & Placement Management System
Job Offers Data Access Object
"""

from dao.db import execute_query, execute_one, execute_insert, execute_update, db_transaction


def get_offer_by_id(offer_id):
    sql = """
        SELECT o.*,
               a.application_code, a.current_stage AS application_stage,
               c.first_name, c.last_name, c.candidate_code, c.email AS candidate_email,
               c.mobile AS candidate_mobile,
               comp.company_name, comp.company_code,
               j.title AS job_title, j.job_code,
               u.full_name AS created_by_name,
               p.placement_id, p.placement_code, p.joining_status, p.actual_joining_date
        FROM offers o
        JOIN applications a ON o.application_id = a.application_id
        JOIN candidates c ON o.candidate_id = c.candidate_id
        JOIN companies comp ON o.company_id = comp.company_id
        JOIN jobs j ON o.job_id = j.job_id
        LEFT JOIN users u ON o.created_by = u.user_id
        LEFT JOIN placements p ON o.offer_id = p.offer_id
        WHERE o.offer_id = %s
    """
    return execute_one(sql, (offer_id,))


def get_offer_by_code(code):
    sql = "SELECT * FROM offers WHERE offer_code = %s"
    return execute_one(sql, (code,))


def get_offer_by_application_id(application_id):
    sql = "SELECT * FROM offers WHERE application_id = %s"
    return execute_one(sql, (application_id,))


def search_offers(search=None, status=None, company_id=None):
    sql = """
        SELECT o.offer_id, o.offer_code, o.designation, o.package_lpa,
               o.offer_date, o.expected_joining_date, o.status,
               c.candidate_id, c.candidate_code, c.first_name, c.last_name,
               comp.company_id, comp.company_name,
               j.job_id, j.title AS job_title,
               p.placement_id, p.joining_status
        FROM offers o
        JOIN candidates c ON o.candidate_id = c.candidate_id
        JOIN companies comp ON o.company_id = comp.company_id
        JOIN jobs j ON o.job_id = j.job_id
        LEFT JOIN placements p ON o.offer_id = p.offer_id
        WHERE 1=1
    """
    params = []

    if search:
        search_pattern = f"%{search.strip()}%"
        sql += """ AND (
            o.offer_code LIKE %s OR
            c.first_name LIKE %s OR
            c.last_name LIKE %s OR
            c.candidate_code LIKE %s OR
            comp.company_name LIKE %s OR
            o.designation LIKE %s
        )"""
        params.extend([search_pattern] * 6)

    if status:
        sql += " AND o.status = %s"
        params.append(status.strip())

    if company_id:
        sql += " AND o.company_id = %s"
        params.append(int(company_id))

    sql += " ORDER BY o.offer_id DESC"
    return execute_query(sql, tuple(params) if params else None)


def create_offer_with_transaction(offer_data):
    """
    Creates an offer and transitions the application stage to OFFERED in a single transaction.
    Rolls back if any step fails.
    """
    with db_transaction() as tx:
        app_id = offer_data["application_id"]

        # Verify application exists and has not already been offered
        tx.execute("SELECT current_stage, candidate_id, job_id FROM applications WHERE application_id = %s", (app_id,))
        app_row = tx.fetchone()
        if not app_row:
            raise ValueError(f"Application #{app_id} does not exist.")

        tx.execute("SELECT offer_id FROM offers WHERE application_id = %s", (app_id,))
        if tx.fetchone():
            raise ValueError(f"An offer already exists for application #{app_id}.")

        sql = """
            INSERT INTO offers (
                offer_code, application_id, candidate_id, company_id,
                job_id, designation, package_lpa, offer_date,
                expected_joining_date, status, remarks, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            offer_data["offer_code"], app_id, offer_data["candidate_id"],
            offer_data["company_id"], offer_data["job_id"], offer_data["designation"],
            offer_data["package_lpa"], offer_data["offer_date"],
            offer_data["expected_joining_date"], offer_data.get("status", "OFFERED"),
            offer_data.get("remarks"), offer_data.get("created_by")
        )
        tx.execute(sql, params)
        offer_id = tx.lastrowid

        # Update application stage to OFFERED
        old_stage = app_row["current_stage"]
        tx.execute("UPDATE applications SET current_stage = 'OFFERED' WHERE application_id = %s", (app_id,))
        tx.execute(
            """INSERT INTO application_history (application_id, old_stage, new_stage, remarks, changed_by)
               VALUES (%s, %s, 'OFFERED', %s, %s)""",
            (app_id, old_stage,
             f"Offer {offer_data['offer_code']} issued for {offer_data['designation']} ({offer_data['package_lpa']} LPA)",
             offer_data.get("created_by"))
        )

        return offer_id


def update_offer_status(offer_id, new_status, remarks=None):
    sql = "UPDATE offers SET status = %s, remarks = COALESCE(%s, remarks) WHERE offer_id = %s"
    return execute_update(sql, (new_status, remarks, offer_id))

