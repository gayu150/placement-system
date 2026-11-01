"""
Recruitment & Placement Management System
Activity Logging Data Access Object
"""

from dao.db import execute_query, execute_insert


def log_activity(user_id, user_name, module, action, record_id, description, ip_address=None):
    """Inserts an audit record into activity_logs table."""
    try:
        sql = """
            INSERT INTO activity_logs (
                user_id, user_name, module, action, record_id, description, ip_address
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (user_id, user_name, module, action, str(record_id) if record_id else None, description, ip_address)
        return execute_insert(sql, params)
    except Exception as e:
        # Avoid crashing primary operations if non-critical audit log fails
        print(f"[ActivityLog Error] Failed to write log: {e}")
        return None


def get_recent_activities(limit=25):
    sql = """
        SELECT log_id, user_id, user_name, module, action, record_id, description,
               ip_address, created_at
        FROM activity_logs
        ORDER BY log_id DESC
        LIMIT %s
    """
    return execute_query(sql, (limit,))


def search_activity_logs(module=None, search=None, limit=100):
    sql = "SELECT * FROM activity_logs WHERE 1=1"
    params = []
    if module:
        sql += " AND module = %s"
        params.append(module.strip())
    if search:
        search_pattern = f"%{search.strip()}%"
        sql += " AND (description LIKE %s OR action LIKE %s OR user_name LIKE %s OR record_id LIKE %s)"
        params.extend([search_pattern] * 4)

    sql += " ORDER BY log_id DESC LIMIT %s"
    params.append(limit)
    return execute_query(sql, tuple(params))

