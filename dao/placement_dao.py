"""
Recruitment & Placement Management System
Placement & Joining Outcomes Data Access Object
"""

from dao.db import execute_query, execute_one, execute_insert, execute_update, db_transaction


def get_placement_by_id(placement_id):
    sql = """
        SELECT p.*,
               o.offer_code, o.offer_date, o.package_lpa AS offered_package,
               c.first_name, c.last_name, c.candidate_code, c.email AS candidate_email,
               c.mobile AS candidate_mobile,
               comp.company_name, comp.company_code,
               j.title AS job_title, j.job_code,
               u.full_name AS recorded_by_name
        FROM placements p
        JOIN offers o ON p.offer_id = o.offer_id
        JOIN candidates c ON p.candidate_id = c.candidate_id
        JOIN companies comp ON p.company_id = comp.company_id
        JOIN jobs j ON p.job_id = j.job_id
        LEFT JOIN users u ON p.recorded_by = u.user_id
        WHERE p.placement_id = %s
    """
    return execute_one(sql, (placement_id,))


def get_placement_by_code(code):
    sql = "SELECT * FROM placements WHERE placement_code = %s"
    return execute_one(sql, (code,))


def get_placement_by_offer_id(offer_id):
    sql = "SELECT * FROM placements WHERE offer_id = %s"
    return execute_one(sql, (offer_id,))


def search_placements(search=None, joining_status=None, company_id=None):
    sql = """
        SELECT p.placement_id, p.placement_code, p.designation, p.final_package_lpa,
               p.expected_joining_date, p.actual_joining_date, p.joining_status,
               o.offer_code,
               c.candidate_id, c.candidate_code, c.first_name, c.last_name,
               comp.company_id, comp.company_name,
               j.job_id, j.title AS job_title
        FROM placements p
        JOIN offers o ON p.offer_id = o.offer_id
        JOIN candidates c ON p.candidate_id = c.candidate_id
        JOIN companies comp ON p.company_id = comp.company_id
        JOIN jobs j ON p.job_id = j.job_id
        WHERE 1=1
    """
    params = []

    if search:
        search_pattern = f"%{search.strip()}%"
        sql += """ AND (
            p.placement_code LIKE %s OR
            o.offer_code LIKE %s OR
            c.first_name LIKE %s OR
            c.last_name LIKE %s OR
            c.candidate_code LIKE %s OR
            comp.company_name LIKE %s OR
            p.designation LIKE %s
        )"""
        params.extend([search_pattern] * 7)

    if joining_status:
        sql += " AND p.joining_status = %s"
        params.append(joining_status.strip())

    if company_id:
        sql += " AND p.company_id = %s"
        params.append(int(company_id))

    sql += " ORDER BY p.placement_id DESC"
    return execute_query(sql, tuple(params) if params else None)


def record_placement_with_transaction(placement_data):
    """
    Records a placement for an accepted offer in a transaction.
    If joining_status is JOINED, automatically updates:
      - Offer status to ACCEPTED
      - Application current_stage to JOINED
      - Application history
      - Candidate placement_status to Placed
    All steps rolled back if any fails.
    """
    with db_transaction() as tx:
        offer_id = placement_data["offer_id"]

        # Verify offer exists
        tx.execute("SELECT * FROM offers WHERE offer_id = %s", (offer_id,))
        offer = tx.fetchone()
        if not offer:
            raise ValueError(f"Offer #{offer_id} does not exist.")

        # Prevent duplicate placement per offer
        tx.execute("SELECT placement_id FROM placements WHERE offer_id = %s", (offer_id,))
        if tx.fetchone():
            raise ValueError(f"Placement outcome has already been recorded for offer #{offer_id}.")

        sql = """
            INSERT INTO placements (
                placement_code, offer_id, candidate_id, company_id,
                job_id, designation, final_package_lpa, expected_joining_date,
                actual_joining_date, joining_status, remarks, recorded_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            placement_data["placement_code"], offer_id,
            placement_data["candidate_id"], placement_data["company_id"],
            placement_data["job_id"], placement_data["designation"],
            placement_data["final_package_lpa"], placement_data["expected_joining_date"],
            placement_data.get("actual_joining_date") or None,
            placement_data.get("joining_status", "PENDING"),
            placement_data.get("remarks"), placement_data.get("recorded_by")
        )
        tx.execute(sql, params)
        placement_id = tx.lastrowid

        # Make sure offer is marked ACCEPTED
        tx.execute("UPDATE offers SET status = 'ACCEPTED' WHERE offer_id = %s", (offer_id,))

        joining_status = placement_data.get("joining_status", "PENDING")
        cand_id = placement_data["candidate_id"]
        app_id = offer["application_id"]

        if joining_status == "JOINED":
            # Update application stage to JOINED
            tx.execute("SELECT current_stage FROM applications WHERE application_id = %s", (app_id,))
            app_row = tx.fetchone()
            old_stage = app_row["current_stage"] if app_row else "OFFERED"

            tx.execute("UPDATE applications SET current_stage = 'JOINED' WHERE application_id = %s", (app_id,))
            tx.execute(
                """INSERT INTO application_history (application_id, old_stage, new_stage, remarks, changed_by)
                   VALUES (%s, %s, 'JOINED', %s, %s)""",
                (app_id, old_stage,
                 f"Placement confirmed with code {placement_data['placement_code']}. Joining verified.",
                 placement_data.get("recorded_by"))
            )

            # Update candidate placement status
            tx.execute("UPDATE candidates SET placement_status = 'Placed' WHERE candidate_id = %s", (cand_id,))

        elif joining_status in ["NOT_JOINED", "NO_SHOW"]:
            tx.execute("UPDATE candidates SET placement_status = 'Unplaced' WHERE candidate_id = %s", (cand_id,))

        return placement_id


def update_joining_outcome_with_transaction(placement_id, joining_status, actual_joining_date=None, remarks=None, user_id=None):
    """
    Updates joining status and syncs application stage / candidate status in a transaction.
    """
    with db_transaction() as tx:
        tx.execute("SELECT * FROM placements WHERE placement_id = %s", (placement_id,))
        p = tx.fetchone()
        if not p:
            raise ValueError(f"Placement #{placement_id} not found.")

        tx.execute("""
            UPDATE placements SET
                joining_status = %s,
                actual_joining_date = COALESCE(%s, actual_joining_date),
                remarks = COALESCE(%s, remarks)
            WHERE placement_id = %s
        """, (joining_status, actual_joining_date, remarks, placement_id))

        offer_id = p["offer_id"]
        tx.execute("SELECT application_id FROM offers WHERE offer_id = %s", (offer_id,))
        offer = tx.fetchone()

        cand_id = p["candidate_id"]

        if offer:
            app_id = offer["application_id"]
            if joining_status == "JOINED":
                tx.execute("SELECT current_stage FROM applications WHERE application_id = %s", (app_id,))
                app_row = tx.fetchone()
                old_stage = app_row["current_stage"] if app_row else "OFFERED"

                tx.execute("UPDATE applications SET current_stage = 'JOINED' WHERE application_id = %s", (app_id,))
                tx.execute(
                    """INSERT INTO application_history (application_id, old_stage, new_stage, remarks, changed_by)
                       VALUES (%s, %s, 'JOINED', %s, %s)""",
                    (app_id, old_stage, f"Joining verified on {actual_joining_date or 'today'}", user_id)
                )
                tx.execute("UPDATE candidates SET placement_status = 'Placed' WHERE candidate_id = %s", (cand_id,))
            elif joining_status in ["NOT_JOINED", "NO_SHOW"]:
                tx.execute("UPDATE candidates SET placement_status = 'Unplaced' WHERE candidate_id = %s", (cand_id,))

        return True

