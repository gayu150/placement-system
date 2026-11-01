"""
Recruitment & Placement Management System
Company Data Access Object
"""

from dao.db import execute_query, execute_one, execute_insert, execute_update


def get_company_by_id(company_id):
    sql = "SELECT * FROM companies WHERE company_id = %s"
    return execute_one(sql, (company_id,))


def get_company_by_code(code):
    sql = "SELECT * FROM companies WHERE company_code = %s"
    return execute_one(sql, (code,))


def search_companies(search=None, industry=None, status=None):
    sql = "SELECT * FROM companies WHERE 1=1"
    params = []

    if search:
        search_pattern = f"%{search.strip()}%"
        sql += """ AND (
            company_code LIKE %s OR
            company_name LIKE %s OR
            location LIKE %s OR
            hr_name LIKE %s OR
            hr_email LIKE %s
        )"""
        params.extend([search_pattern] * 5)

    if industry:
        sql += " AND industry = %s"
        params.append(industry.strip())

    if status:
        sql += " AND status = %s"
        params.append(status.strip())

    sql += " ORDER BY company_id DESC"
    return execute_query(sql, tuple(params) if params else None)


def get_active_companies():
    sql = "SELECT company_id, company_code, company_name, location, industry FROM companies WHERE status = 'Active' ORDER BY company_name ASC"
    return execute_query(sql)


def has_jobs_or_history(company_id):
    """Checks if company has any associated jobs or placement records."""
    sql = "SELECT COUNT(*) AS count FROM jobs WHERE company_id = %s"
    res = execute_one(sql, (company_id,))
    return res and res["count"] > 0


def create_company(company_data):
    sql = """
        INSERT INTO companies (
            company_code, company_name, industry, website,
            location, company_type, hr_name, hr_email, hr_phone, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        company_data["company_code"], company_data["company_name"],
        company_data["industry"], company_data.get("website") or None,
        company_data["location"], company_data.get("company_type", "Service"),
        company_data["hr_name"], company_data["hr_email"],
        company_data["hr_phone"], company_data.get("status", "Active")
    )
    return execute_insert(sql, params)


def update_company(company_id, company_data):
    sql = """
        UPDATE companies SET
            company_name = %s,
            industry = %s,
            website = %s,
            location = %s,
            company_type = %s,
            hr_name = %s,
            hr_email = %s,
            hr_phone = %s,
            status = %s
        WHERE company_id = %s
    """
    params = (
        company_data["company_name"], company_data["industry"],
        company_data.get("website") or None, company_data["location"],
        company_data.get("company_type", "Service"), company_data["hr_name"],
        company_data["hr_email"], company_data["hr_phone"],
        company_data.get("status", "Active"), company_id
    )
    return execute_update(sql, params)


def set_company_status(company_id, status):
    sql = "UPDATE companies SET status = %s WHERE company_id = %s"
    return execute_update(sql, (status, company_id))


def get_company_jobs(company_id):
    sql = """
        SELECT j.*, (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS app_count
        FROM jobs j
        WHERE j.company_id = %s
        ORDER BY j.job_id DESC
    """
    return execute_query(sql, (company_id,))

