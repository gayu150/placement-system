"""
Recruitment & Placement Management System
User & Role Data Access Object
"""

from dao.db import execute_query, execute_one, execute_insert, execute_update


def get_user_by_id(user_id):
    sql = """
        SELECT u.user_id, u.role_id, u.username, u.email, u.password_hash,
               u.full_name, u.is_active, u.created_at, u.updated_at,
               r.role_name, r.description AS role_description
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE u.user_id = %s
    """
    return execute_one(sql, (user_id,))


def get_user_by_username(username):
    sql = """
        SELECT u.user_id, u.role_id, u.username, u.email, u.password_hash,
               u.full_name, u.is_active, u.created_at, u.updated_at,
               r.role_name, r.description AS role_description
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE u.username = %s
    """
    return execute_one(sql, (username,))


def get_user_by_email(email):
    sql = """
        SELECT u.user_id, u.role_id, u.username, u.email, u.password_hash,
               u.full_name, u.is_active, r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE u.email = %s
    """
    return execute_one(sql, (email,))


def get_all_users():
    sql = """
        SELECT u.user_id, u.role_id, u.username, u.email,
               u.full_name, u.is_active, u.created_at,
               r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        ORDER BY u.user_id ASC
    """
    return execute_query(sql)


def get_roles():
    sql = "SELECT role_id, role_name, description FROM roles ORDER BY role_id ASC"
    return execute_query(sql)


def create_user(role_id, username, email, password_hash, full_name, is_active=1):
    sql = """
        INSERT INTO users (role_id, username, email, password_hash, full_name, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    return execute_insert(sql, (role_id, username, email, password_hash, full_name, is_active))


def update_user_status(user_id, is_active):
    sql = "UPDATE users SET is_active = %s WHERE user_id = %s"
    return execute_update(sql, (is_active, user_id))

