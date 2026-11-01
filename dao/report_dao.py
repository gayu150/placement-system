"""
Recruitment & Placement Management System
Reports & Dashboard Aggregation Data Access Object
"""

from dao.db import execute_query, execute_one


def get_dashboard_metrics():
    """
    Retrieves key operational metrics for the dashboard using live database queries.
    """
    metrics = {}

    # Total and active candidates
    cand_row = execute_one("""
        SELECT
            COUNT(*) AS total_candidates,
            SUM(CASE WHEN profile_status = 'Active' THEN 1 ELSE 0 END) AS active_candidates,
            SUM(CASE WHEN placement_status = 'Placed' THEN 1 ELSE 0 END) AS placed_candidates
        FROM candidates
    """) or {}
    metrics["total_candidates"] = cand_row.get("total_candidates", 0)
    metrics["active_candidates"] = cand_row.get("active_candidates", 0) or 0
    metrics["placed_candidates"] = cand_row.get("placed_candidates", 0) or 0

    # Total companies and active companies
    comp_row = execute_one("""
        SELECT
            COUNT(*) AS total_companies,
            SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) AS active_companies
        FROM companies
    """) or {}
    metrics["total_companies"] = comp_row.get("total_companies", 0)
    metrics["active_companies"] = comp_row.get("active_companies", 0) or 0

    # Open jobs and total openings
    job_row = execute_one("""
        SELECT
            COUNT(*) AS open_jobs_count,
            COALESCE(SUM(openings), 0) AS total_openings
        FROM jobs
        WHERE status = 'Open'
    """) or {}
    metrics["open_jobs"] = job_row.get("open_jobs_count", 0)
    metrics["total_openings"] = job_row.get("total_openings", 0) or 0

    # Offers and confirmed placements
    offer_row = execute_one("""
        SELECT
            COUNT(*) AS total_offers,
            SUM(CASE WHEN status = 'ACCEPTED' THEN 1 ELSE 0 END) AS accepted_offers
        FROM offers
    """) or {}
    metrics["total_offers"] = offer_row.get("total_offers", 0)
    metrics["accepted_offers"] = offer_row.get("accepted_offers", 0) or 0

    placement_row = execute_one("""
        SELECT
            COUNT(*) AS confirmed_placements,
            COALESCE(AVG(final_package_lpa), 0.0) AS avg_package
        FROM placements
        WHERE joining_status = 'JOINED'
    """) or {}
    metrics["confirmed_placements"] = placement_row.get("confirmed_placements", 0)
    metrics["avg_package"] = round(float(placement_row.get("avg_package", 0.0) or 0.0), 2)

    # Applications by stage
    metrics["stage_counts"] = execute_query("""
        SELECT current_stage, COUNT(*) AS count
        FROM applications
        GROUP BY current_stage
        ORDER BY count DESC
    """)

    # Upcoming interviews (scheduled on or after current date or pending)
    metrics["upcoming_interviews"] = execute_query("""
        SELECT ir.interview_id, ir.round_number, ir.round_name, ir.scheduled_date,
               ir.scheduled_time, ir.interview_mode, ir.status,
               c.first_name, c.last_name, c.candidate_code,
               j.title AS job_title, comp.company_name
        FROM interview_rounds ir
        JOIN applications a ON ir.application_id = a.application_id
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies comp ON j.company_id = comp.company_id
        WHERE ir.status IN ('SCHEDULED', 'RESCHEDULED')
        ORDER BY ir.scheduled_date ASC, ir.scheduled_time ASC
        LIMIT 5
    """)

    # Selected candidates awaiting offers or joining
    metrics["selected_candidates"] = execute_query("""
        SELECT a.application_id, a.application_code,
               c.candidate_id, c.candidate_code, c.first_name, c.last_name, c.primary_technology,
               j.title AS job_title, comp.company_name, a.current_stage
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies comp ON j.company_id = comp.company_id
        WHERE a.current_stage IN ('SELECTED', 'OFFERED')
        ORDER BY a.updated_at DESC
        LIMIT 5
    """)

    return metrics


def report_candidates_by_technology(passing_year=None):
    sql = """
        SELECT primary_technology,
               COUNT(*) AS candidate_count,
               SUM(CASE WHEN placement_status = 'Placed' THEN 1 ELSE 0 END) AS placed_count,
               ROUND(AVG(percentage), 2) AS avg_percentage
        FROM candidates
        WHERE 1=1
    """
    params = []
    if passing_year:
        sql += " AND passing_year = %s"
        params.append(int(passing_year))

    sql += " GROUP BY primary_technology ORDER BY candidate_count DESC"
    rows = execute_query(sql, tuple(params) if params else None)

    # Compute percentages
    total = sum(r["candidate_count"] for r in rows) if rows else 0
    for r in rows:
        r["percentage_of_total"] = round((r["candidate_count"] / total * 100), 1) if total > 0 else 0
    return rows


def report_open_jobs_by_company():
    sql = """
        SELECT c.company_id, c.company_name, c.industry, c.location,
               COUNT(j.job_id) AS open_jobs_count,
               COALESCE(SUM(j.openings), 0) AS total_openings,
               ROUND(AVG(j.min_package), 2) AS avg_min_package,
               ROUND(AVG(j.max_package), 2) AS avg_max_package
        FROM companies c
        LEFT JOIN jobs j ON c.company_id = j.company_id AND j.status = 'Open'
        GROUP BY c.company_id, c.company_name, c.industry, c.location
        HAVING open_jobs_count > 0
        ORDER BY total_openings DESC, open_jobs_count DESC
    """
    return execute_query(sql)


def report_applications_by_status(job_id=None, company_id=None):
    sql = """
        SELECT a.current_stage,
               COUNT(*) AS total_count,
               SUM(CASE WHEN a.eligibility_status = 'ELIGIBLE' THEN 1 ELSE 0 END) AS eligible_count,
               SUM(CASE WHEN a.is_override = 1 THEN 1 ELSE 0 END) AS override_count
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE 1=1
    """
    params = []
    if job_id:
        sql += " AND a.job_id = %s"
        params.append(int(job_id))
    if company_id:
        sql += " AND j.company_id = %s"
        params.append(int(company_id))

    sql += " GROUP BY a.current_stage ORDER BY total_count DESC"
    return execute_query(sql, tuple(params) if params else None)


def report_recruitment_funnel():
    """
    Calculates counts and conversions through standard recruitment funnel stages:
    Applied -> Eligibility Verified -> Shortlisted -> Interview Scheduled -> Interviewed -> Selected -> Offered -> Joined
    """
    total_apps_row = execute_one("SELECT COUNT(*) AS total FROM applications")
    total_apps = total_apps_row["total"] if total_apps_row else 0

    stages = [
        ("APPLIED", "Applied"),
        ("ELIGIBILITY_VERIFIED", "Eligibility Verified"),
        ("SHORTLISTED", "Shortlisted"),
        ("INTERVIEW_SCHEDULED", "Interview Scheduled"),
        ("INTERVIEWED", "Interviewed"),
        ("SELECTED", "Selected"),
        ("OFFERED", "Offered"),
        ("JOINED", "Joined")
    ]

    funnel_data = []
    # To track funnel accurately, count candidates who have reached or passed each stage
    for stage_key, stage_label in stages:
        # A candidate reached stage X if history has it or current_stage matches or passed
        sql = """
            SELECT COUNT(DISTINCT application_id) AS count
            FROM application_history
            WHERE new_stage = %s
        """
        row = execute_one(sql, (stage_key,))
        count = row["count"] if row else 0

        # Fallback to current_stage if not in history
        curr_row = execute_one("SELECT COUNT(*) AS count FROM applications WHERE current_stage = %s", (stage_key,))
        curr_count = curr_row["count"] if curr_row else 0
        effective_count = max(count, curr_count)

        pct = round((effective_count / total_apps * 100), 1) if total_apps > 0 else 0
        funnel_data.append({
            "stage_key": stage_key,
            "stage_label": stage_label,
            "count": effective_count,
            "percentage": pct
        })

    return funnel_data


def report_company_wise_placements():
    sql = """
        SELECT c.company_name, c.industry, c.location,
               COUNT(p.placement_id) AS total_placed,
               ROUND(AVG(p.final_package_lpa), 2) AS avg_package,
               MAX(p.final_package_lpa) AS highest_package,
               MIN(p.final_package_lpa) AS lowest_package
        FROM placements p
        JOIN companies c ON p.company_id = c.company_id
        WHERE p.joining_status = 'JOINED'
        GROUP BY c.company_id, c.company_name, c.industry, c.location
        ORDER BY total_placed DESC, avg_package DESC
    """
    return execute_query(sql)


def report_technology_wise_placements():
    sql = """
        SELECT c.primary_technology,
               COUNT(p.placement_id) AS placed_count,
               ROUND(AVG(p.final_package_lpa), 2) AS avg_package,
               MAX(p.final_package_lpa) AS highest_package
        FROM placements p
        JOIN candidates c ON p.candidate_id = c.candidate_id
        WHERE p.joining_status = 'JOINED'
        GROUP BY c.primary_technology
        ORDER BY placed_count DESC, avg_package DESC
    """
    return execute_query(sql)


def report_recruiter_performance():
    sql = """
        SELECT u.user_id, u.full_name, u.email, r.role_name,
               (SELECT COUNT(*) FROM jobs WHERE created_by = u.user_id) AS jobs_posted,
               (SELECT COUNT(*) FROM interview_rounds WHERE scheduled_by = u.user_id) AS interviews_scheduled,
               (SELECT COUNT(*) FROM interview_feedback WHERE submitted_by = u.user_id) AS feedback_submitted,
               (SELECT COUNT(*) FROM offers WHERE created_by = u.user_id) AS offers_created,
               (SELECT COUNT(*) FROM placements WHERE recorded_by = u.user_id) AS placements_recorded
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE r.role_name IN ('Recruiter', 'Placement Officer', 'Admin')
        ORDER BY u.user_id ASC
    """
    return execute_query(sql)


def report_pending_upcoming_interviews():
    sql = """
        SELECT ir.interview_id, ir.round_number, ir.round_name,
               ir.scheduled_date, ir.scheduled_time, ir.interview_mode,
               ir.interviewer_name, ir.meeting_link_or_venue, ir.status,
               c.first_name, c.last_name, c.candidate_code, c.email,
               j.title AS job_title, comp.company_name
        FROM interview_rounds ir
        JOIN applications a ON ir.application_id = a.application_id
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies comp ON j.company_id = comp.company_id
        WHERE ir.status IN ('SCHEDULED', 'RESCHEDULED')
        ORDER BY ir.scheduled_date ASC, ir.scheduled_time ASC
    """
    return execute_query(sql)


def report_offer_to_joining_conversion():
    sql = """
        SELECT
            COUNT(o.offer_id) AS total_offers,
            SUM(CASE WHEN o.status = 'ACCEPTED' THEN 1 ELSE 0 END) AS accepted_offers,
            SUM(CASE WHEN o.status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected_offers,
            SUM(CASE WHEN p.joining_status = 'JOINED' THEN 1 ELSE 0 END) AS confirmed_joined,
            SUM(CASE WHEN p.joining_status = 'NO_SHOW' THEN 1 ELSE 0 END) AS no_shows,
            SUM(CASE WHEN p.joining_status = 'DEFERRED' THEN 1 ELSE 0 END) AS deferred
        FROM offers o
        LEFT JOIN placements p ON o.offer_id = p.offer_id
    """
    row = execute_one(sql) or {}
    total = row.get("total_offers", 0) or 0
    accepted = row.get("accepted_offers", 0) or 0
    joined = row.get("confirmed_joined", 0) or 0

    row["acceptance_rate"] = round((accepted / total * 100), 1) if total > 0 else 0
    row["joining_rate"] = round((joined / total * 100), 1) if total > 0 else 0
    return row


def report_open_job_aging():
    """Calculates days since posted for all open jobs."""
    sql = """
        SELECT j.job_id, j.job_code, j.title, j.location, j.openings,
               j.posted_date, j.deadline,
               c.company_name,
               (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS applicants_count
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        WHERE j.status = 'Open'
        ORDER BY j.posted_date ASC
    """
    rows = execute_query(sql)
    from datetime import date, datetime
    today = date.today()
    for r in rows:
        posted = r["posted_date"]
        if isinstance(posted, str):
            posted = datetime.strptime(posted[:10], "%Y-%m-%d").date()
        r["days_open"] = (today - posted).days if posted else 0
    return rows


def report_placed_vs_unplaced():
    sql = """
        SELECT placement_status,
               COUNT(*) AS count
        FROM candidates
        WHERE profile_status = 'Active'
        GROUP BY placement_status
        ORDER BY count DESC
    """
    rows = execute_query(sql)
    total = sum(r["count"] for r in rows) if rows else 0
    for r in rows:
        r["percentage"] = round((r["count"] / total * 100), 1) if total > 0 else 0
    return {"total": total, "breakdown": rows}

