"""
Recruitment & Placement Management System
Database Initialization Script
Sets up tables and sample seed data for MySQL or SQLite.
Usage:
    python sql/init_database.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from dao.db import get_active_engine, HAS_MYSQL_CONNECTOR


def init_sqlite(db_path=None):
    """Initialize SQLite database with full schema and sample data."""
    import sqlite3
    path = db_path or Config.SQLITE_DB_PATH
    print(f"[Init DB] Initializing SQLite database at: {path}")

    # Remove existing db file if requested or fresh start
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    schema_statements = [
        # Roles
        """CREATE TABLE IF NOT EXISTS roles (
            role_id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_name TEXT NOT NULL UNIQUE,
            description TEXT
        );""",

        # Users
        """CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles (role_id)
        );""",

        # Skills
        """CREATE TABLE IF NOT EXISTS skills (
            skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT 'General'
        );""",

        # Candidates
        """CREATE TABLE IF NOT EXISTS candidates (
            candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_code TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            mobile TEXT NOT NULL UNIQUE,
            date_of_birth DATE,
            gender TEXT,
            qualification TEXT NOT NULL,
            college TEXT NOT NULL,
            university TEXT NOT NULL,
            passing_year INTEGER NOT NULL,
            percentage REAL NOT NULL,
            cgpa REAL,
            backlog_count INTEGER NOT NULL DEFAULT 0,
            primary_technology TEXT NOT NULL,
            skill_proficiency TEXT NOT NULL DEFAULT 'Intermediate',
            experience_years REAL NOT NULL DEFAULT 0.0,
            current_location TEXT NOT NULL,
            preferred_location TEXT NOT NULL,
            profile_status TEXT NOT NULL DEFAULT 'Active',
            placement_status TEXT NOT NULL DEFAULT 'Unplaced',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (percentage >= 0.0 AND percentage <= 100.0),
            CHECK (backlog_count >= 0),
            CHECK (profile_status IN ('Active', 'Inactive')),
            CHECK (placement_status IN ('Unplaced', 'In Process', 'Placed', 'Opted Out'))
        );""",

        # Candidate Skills
        """CREATE TABLE IF NOT EXISTS candidate_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            proficiency_level TEXT NOT NULL DEFAULT 'Intermediate',
            FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skills (skill_id) ON DELETE RESTRICT,
            UNIQUE (candidate_id, skill_id)
        );""",

        # Companies
        """CREATE TABLE IF NOT EXISTS companies (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_code TEXT NOT NULL UNIQUE,
            company_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            website TEXT,
            location TEXT NOT NULL,
            company_type TEXT NOT NULL DEFAULT 'Service',
            hr_name TEXT NOT NULL,
            hr_email TEXT NOT NULL,
            hr_phone TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (status IN ('Active', 'Inactive'))
        );""",

        # Jobs
        """CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_code TEXT NOT NULL UNIQUE,
            company_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            employment_type TEXT NOT NULL DEFAULT 'Full-time',
            location TEXT NOT NULL,
            openings INTEGER NOT NULL,
            min_package REAL NOT NULL,
            max_package REAL NOT NULL,
            qualification_req TEXT NOT NULL,
            min_percentage REAL NOT NULL DEFAULT 60.0,
            min_passing_year INTEGER NOT NULL,
            max_passing_year INTEGER NOT NULL,
            max_backlogs INTEGER NOT NULL DEFAULT 0,
            experience_req REAL NOT NULL DEFAULT 0.0,
            posted_date DATE NOT NULL,
            deadline DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            created_by INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (company_id),
            FOREIGN KEY (created_by) REFERENCES users (user_id),
            CHECK (openings > 0),
            CHECK (min_package <= max_package),
            CHECK (deadline >= posted_date),
            CHECK (status IN ('Draft', 'Open', 'Closed', 'Cancelled'))
        );""",

        # Job Skills
        """CREATE TABLE IF NOT EXISTS job_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            is_mandatory INTEGER NOT NULL DEFAULT 1,
            min_proficiency TEXT NOT NULL DEFAULT 'Intermediate',
            FOREIGN KEY (job_id) REFERENCES jobs (job_id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skills (skill_id),
            UNIQUE (job_id, skill_id)
        );""",

        # Applications
        """CREATE TABLE IF NOT EXISTS applications (
            application_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_code TEXT NOT NULL UNIQUE,
            candidate_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            applied_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            current_stage TEXT NOT NULL DEFAULT 'APPLIED',
            eligibility_status TEXT NOT NULL,
            eligibility_remarks TEXT,
            is_override INTEGER NOT NULL DEFAULT 0,
            override_reason TEXT,
            override_by INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id),
            FOREIGN KEY (job_id) REFERENCES jobs (job_id),
            FOREIGN KEY (override_by) REFERENCES users (user_id),
            UNIQUE (candidate_id, job_id),
            CHECK (current_stage IN ('APPLIED', 'ELIGIBILITY_VERIFIED', 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'SELECTED', 'OFFERED', 'JOINED', 'REJECTED', 'WITHDRAWN')),
            CHECK (eligibility_status IN ('ELIGIBLE', 'NOT_ELIGIBLE'))
        );""",

        # Application History
        """CREATE TABLE IF NOT EXISTS application_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            old_stage TEXT NOT NULL,
            new_stage TEXT NOT NULL,
            remarks TEXT,
            changed_by INTEGER,
            changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications (application_id) ON DELETE CASCADE,
            FOREIGN KEY (changed_by) REFERENCES users (user_id)
        );""",

        # Interview Rounds
        """CREATE TABLE IF NOT EXISTS interview_rounds (
            interview_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            round_name TEXT NOT NULL,
            scheduled_date DATE NOT NULL,
            scheduled_time TIME NOT NULL,
            interview_mode TEXT NOT NULL DEFAULT 'Online',
            interviewer_name TEXT NOT NULL,
            meeting_link_or_venue TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'SCHEDULED',
            scheduled_by INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications (application_id) ON DELETE CASCADE,
            FOREIGN KEY (scheduled_by) REFERENCES users (user_id),
            UNIQUE (application_id, round_number),
            CHECK (status IN ('SCHEDULED', 'COMPLETED', 'CANCELLED', 'NO_SHOW', 'RESCHEDULED')),
            CHECK (interview_mode IN ('Online', 'In-person'))
        );""",

        # Interview Feedback
        """CREATE TABLE IF NOT EXISTS interview_feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER NOT NULL UNIQUE,
            technical_rating INTEGER NOT NULL,
            communication_rating INTEGER NOT NULL,
            problem_solving_rating INTEGER NOT NULL,
            overall_rating INTEGER NOT NULL,
            recommendation TEXT NOT NULL,
            remarks TEXT NOT NULL,
            submitted_by INTEGER,
            submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (interview_id) REFERENCES interview_rounds (interview_id) ON DELETE CASCADE,
            FOREIGN KEY (submitted_by) REFERENCES users (user_id),
            CHECK (technical_rating BETWEEN 1 AND 5),
            CHECK (communication_rating BETWEEN 1 AND 5),
            CHECK (problem_solving_rating BETWEEN 1 AND 5),
            CHECK (overall_rating BETWEEN 1 AND 5),
            CHECK (recommendation IN ('NEXT_ROUND', 'SELECTED', 'REJECTED', 'ON_HOLD'))
        );""",

        # Offers
        """CREATE TABLE IF NOT EXISTS offers (
            offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_code TEXT NOT NULL UNIQUE,
            application_id INTEGER NOT NULL UNIQUE,
            candidate_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            designation TEXT NOT NULL,
            package_lpa REAL NOT NULL,
            offer_date DATE NOT NULL,
            expected_joining_date DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'OFFERED',
            remarks TEXT,
            created_by INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications (application_id),
            FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id),
            FOREIGN KEY (company_id) REFERENCES companies (company_id),
            FOREIGN KEY (job_id) REFERENCES jobs (job_id),
            FOREIGN KEY (created_by) REFERENCES users (user_id),
            CHECK (status IN ('OFFERED', 'ACCEPTED', 'REJECTED', 'EXPIRED', 'WITHDRAWN'))
        );""",

        # Placements
        """CREATE TABLE IF NOT EXISTS placements (
            placement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            placement_code TEXT NOT NULL UNIQUE,
            offer_id INTEGER NOT NULL UNIQUE,
            candidate_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            designation TEXT NOT NULL,
            final_package_lpa REAL NOT NULL,
            expected_joining_date DATE NOT NULL,
            actual_joining_date DATE,
            joining_status TEXT NOT NULL DEFAULT 'PENDING',
            remarks TEXT,
            recorded_by INTEGER,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (offer_id) REFERENCES offers (offer_id),
            FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id),
            FOREIGN KEY (company_id) REFERENCES companies (company_id),
            FOREIGN KEY (job_id) REFERENCES jobs (job_id),
            FOREIGN KEY (recorded_by) REFERENCES users (user_id),
            CHECK (joining_status IN ('PENDING', 'JOINED', 'NOT_JOINED', 'DEFERRED', 'NO_SHOW'))
        );""",

        # Activity Logs
        """CREATE TABLE IF NOT EXISTS activity_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            module TEXT NOT NULL,
            action TEXT NOT NULL,
            record_id TEXT,
            description TEXT NOT NULL,
            ip_address TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        );"""
    ]

    for stmt in schema_statements:
        cursor.execute(stmt)

    # Seed Sample Data
    demo_hash = 'scrypt:32768:8:1$yBjqZhWvUfyg3Lie$58ea78eb05b195a752da78cc9d7d5fe6c289d1d932b1f597bf7699f8e379b9a73a3dc30e26481bc73c13ae5844325420f96c89bc6a1f1fc4aa37fdbba3adc008'

    # Roles
    cursor.executemany(
        "INSERT OR IGNORE INTO roles (role_id, role_name, description) VALUES (?, ?, ?);",
        [
            (1, 'Admin', 'Full administrative access to manage users, system settings, master data, and audits'),
            (2, 'Recruiter', 'Manages jobs, candidate sourcing, application workflows, and interview scheduling'),
            (3, 'Placement Officer', 'Oversees student placements, eligibility rules, company relations, offers, and analytics')
        ]
    )

    # Users
    cursor.executemany(
        "INSERT OR IGNORE INTO users (user_id, role_id, username, email, password_hash, full_name, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        [
            (1, 1, 'admin', 'admin@placement.edu', demo_hash, 'Dr. Rajesh Sharma (Director)', 1, '2026-01-10 09:00:00'),
            (2, 2, 'recruiter', 'recruiter@placement.edu', demo_hash, 'Priya Menon (Lead Recruiter)', 1, '2026-01-12 10:30:00'),
            (3, 3, 'placement', 'officer@placement.edu', demo_hash, 'Vikram Rathore (Placement Officer)', 1, '2026-01-15 11:15:00')
        ]
    )

    # Skills
    skills_data = [
        (1, 'Python', 'Backend'), (2, 'Java', 'Backend'), (3, 'SQL', 'Database'),
        (4, 'React', 'Frontend'), (5, 'JavaScript', 'Frontend'), (6, 'Node.js', 'Backend'),
        (7, 'Spring Boot', 'Backend'), (8, 'Django', 'Backend'), (9, 'Data Analysis', 'Data Science'),
        (10, 'Machine Learning', 'Data Science'), (11, 'AWS', 'Cloud'), (12, 'Docker', 'DevOps'),
        (13, 'Git', 'Tools'), (14, 'Flutter', 'Mobile'), (15, 'C++', 'Core')
    ]
    cursor.executemany("INSERT OR IGNORE INTO skills (skill_id, skill_name, category) VALUES (?, ?, ?);", skills_data)

    # Companies
    companies_data = [
        (1, 'COMP-101', 'TechNova Solutions', 'Information Technology', 'https://technova.example.com', 'Bengaluru', 'Product', 'Sunita Rao', 'sunita.rao@technova.example.com', '9876543210', 'Active'),
        (2, 'COMP-102', 'CloudZen Systems', 'Cloud & DevOps', 'https://cloudzen.example.com', 'Hyderabad', 'Service', 'Anand Kulkarni', 'anand.k@cloudzen.example.com', '9876543211', 'Active'),
        (3, 'COMP-103', 'Apex Global Fintech', 'Financial Technology', 'https://apexfintech.example.com', 'Mumbai', 'Product', 'Neha Verma', 'neha.v@apexfintech.example.com', '9876543212', 'Active'),
        (4, 'COMP-104', 'Dataminds Analytics', 'AI & Data Science', 'https://dataminds.example.com', 'Pune', 'Startup', 'Rohan Gupta', 'rohan@dataminds.example.com', '9876543213', 'Active'),
        (5, 'COMP-105', 'CyberEdge Networks', 'Cybersecurity', 'https://cyberedge.example.com', 'Noida', 'MNC', 'Meera Iyer', 'meera.iyer@cyberedge.example.com', '9876543214', 'Active'),
        (6, 'COMP-106', 'Legacy Soft Technologies', 'Enterprise IT', 'https://legacysoft.example.com', 'Chennai', 'Service', 'Suresh Nair', 'suresh@legacysoft.example.com', '9876543215', 'Inactive')
    ]
    cursor.executemany("INSERT OR IGNORE INTO companies (company_id, company_code, company_name, industry, website, location, company_type, hr_name, hr_email, hr_phone, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", companies_data)

    # Candidates
    candidates_data = [
        (1, 'CAND-2026-001', 'Aarav', 'Sharma', 'aarav.sharma@student.edu', '9123456701', '2003-05-14', 'Male', 'B.Tech', 'Govt Engineering College', 'State Technical University', 2026, 84.50, 8.75, 0, 'Python', 'Advanced', 0.50, 'Bengaluru', 'Bengaluru, Hyderabad', 'Active', 'Placed'),
        (2, 'CAND-2026-002', 'Sneha', 'Patil', 'sneha.patil@student.edu', '9123456702', '2003-08-22', 'Female', 'B.Tech', 'National Institute of Tech', 'State Technical University', 2026, 78.20, 8.10, 0, 'Java', 'Advanced', 0.00, 'Pune', 'Pune, Mumbai, Bengaluru', 'Active', 'In Process'),
        (3, 'CAND-2026-003', 'Rohan', 'Verma', 'rohan.verma@student.edu', '9123456703', '2002-11-05', 'Male', 'MCA', 'Apex Institute of Computer App', 'Metro Central University', 2025, 71.50, 7.40, 1, 'Python', 'Intermediate', 1.00, 'Hyderabad', 'Hyderabad, Bengaluru', 'Active', 'In Process'),
        (4, 'CAND-2026-004', 'Ananya', 'Deshmukh', 'ananya.d@student.edu', '9123456704', '2004-01-30', 'Female', 'B.Tech', 'City College of Engineering', 'State Technical University', 2026, 88.00, 9.10, 0, 'Data Science', 'Advanced', 0.00, 'Mumbai', 'Mumbai, Bengaluru', 'Active', 'In Process'),
        (5, 'CAND-2026-005', 'Karthik', 'Nair', 'karthik.n@student.edu', '9123456705', '2003-03-17', 'Male', 'B.Tech', 'Vidyapeeth College', 'State Technical University', 2026, 62.50, 6.50, 2, 'Java', 'Beginner', 0.00, 'Chennai', 'Chennai, Bengaluru', 'Active', 'Unplaced'),
        (6, 'CAND-2026-006', 'Divya', 'Reddy', 'divya.reddy@student.edu', '9123456706', '2003-09-12', 'Female', 'B.Tech', 'Govt Engineering College', 'State Technical University', 2026, 82.00, 8.50, 0, 'Python', 'Advanced', 0.50, 'Hyderabad', 'Hyderabad, Pune', 'Active', 'Placed'),
        (7, 'CAND-2026-007', 'Aditya', 'Joshi', 'aditya.joshi@student.edu', '9123456707', '2002-07-25', 'Male', 'MCA', 'Institute of Computer Science', 'State Technical University', 2025, 76.00, 7.90, 0, 'React', 'Intermediate', 0.80, 'Bengaluru', 'Bengaluru, Pune', 'Active', 'In Process'),
        (8, 'CAND-2026-008', 'Pooja', 'Hegde', 'pooja.hegde@student.edu', '9123456708', '2003-12-08', 'Female', 'B.Tech', 'Trinity College of Tech', 'State Technical University', 2026, 58.00, 6.10, 3, 'Java', 'Beginner', 0.00, 'Bengaluru', 'Bengaluru', 'Inactive', 'Unplaced')
    ]
    cursor.executemany("INSERT OR IGNORE INTO candidates (candidate_id, candidate_code, first_name, last_name, email, mobile, date_of_birth, gender, qualification, college, university, passing_year, percentage, cgpa, backlog_count, primary_technology, skill_proficiency, experience_years, current_location, preferred_location, profile_status, placement_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", candidates_data)

    # Candidate Skills
    cand_skills_data = [
        (1, 1, 'Advanced'), (1, 3, 'Advanced'), (1, 8, 'Intermediate'), (1, 13, 'Intermediate'),
        (2, 2, 'Advanced'), (2, 7, 'Advanced'), (2, 3, 'Intermediate'),
        (3, 1, 'Intermediate'), (3, 3, 'Intermediate'), (3, 4, 'Intermediate'),
        (4, 1, 'Advanced'), (4, 9, 'Advanced'), (4, 10, 'Intermediate'), (4, 3, 'Advanced'),
        (5, 2, 'Beginner'),
        (6, 1, 'Advanced'), (6, 3, 'Advanced'), (6, 11, 'Intermediate'),
        (7, 4, 'Advanced'), (7, 5, 'Advanced'), (7, 6, 'Intermediate'),
        (8, 2, 'Beginner')
    ]
    cursor.executemany("INSERT OR IGNORE INTO candidate_skills (candidate_id, skill_id, proficiency_level) VALUES (?, ?, ?);", cand_skills_data)

    # Jobs
    jobs_data = [
        (1, 'JOB-2026-001', 1, 'Associate Python Backend Engineer', 'Full-time', 'Bengaluru', 5, 7.50, 10.00, 'B.Tech, MCA', 75.00, 2025, 2026, 0, 0.00, '2026-02-01', '2026-12-31', 'Open', 2),
        (2, 'JOB-2026-002', 2, 'Java Full Stack Developer Trainee', 'Full-time', 'Hyderabad', 10, 6.00, 8.50, 'B.Tech', 70.00, 2025, 2026, 1, 0.00, '2026-02-05', '2026-12-31', 'Open', 2),
        (3, 'JOB-2026-003', 3, 'Graduate Software Engineer - Fintech', 'Full-time', 'Mumbai', 4, 9.00, 12.00, 'B.Tech, MCA', 75.00, 2025, 2026, 0, 0.00, '2026-02-10', '2026-12-31', 'Open', 2),
        (4, 'JOB-2026-004', 4, 'Junior Data & ML Analyst', 'Full-time', 'Pune', 3, 8.00, 11.00, 'B.Tech, MCA', 75.00, 2025, 2026, 0, 0.00, '2026-02-12', '2026-12-31', 'Open', 2),
        (5, 'JOB-2026-005', 5, 'Network Security Associate', 'Full-time', 'Noida', 2, 6.50, 8.00, 'B.Tech', 65.00, 2024, 2026, 1, 0.00, '2026-01-15', '2026-02-28', 'Closed', 2)
    ]
    cursor.executemany("INSERT OR IGNORE INTO jobs (job_id, job_code, company_id, title, employment_type, location, openings, min_package, max_package, qualification_req, min_percentage, min_passing_year, max_passing_year, max_backlogs, experience_req, posted_date, deadline, status, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", jobs_data)

    # Job Skills
    job_skills_data = [
        (1, 1, 1, 'Intermediate'), (1, 3, 1, 'Intermediate'),
        (2, 2, 1, 'Intermediate'), (2, 3, 0, 'Beginner'),
        (3, 1, 1, 'Intermediate'), (3, 3, 1, 'Advanced'),
        (4, 1, 1, 'Intermediate'), (4, 9, 1, 'Intermediate'),
        (5, 11, 1, 'Beginner')
    ]
    cursor.executemany("INSERT OR IGNORE INTO job_skills (job_id, skill_id, is_mandatory, min_proficiency) VALUES (?, ?, ?, ?);", job_skills_data)

    # Applications
    apps_data = [
        (1, 'APP-2026-001', 1, 1, '2026-02-02 10:00:00', 'JOINED', 'ELIGIBLE', 'Meets qualification, passing year (2026), percentage (84.5% >= 75%), 0 backlogs, and possesses required Python and SQL skills.', 0),
        (2, 'APP-2026-002', 2, 2, '2026-02-06 11:30:00', 'INTERVIEW_SCHEDULED', 'ELIGIBLE', 'Meets qualification (B.Tech), passing year (2026), percentage (78.2% >= 70%), 0 backlogs, and Java skills.', 0),
        (3, 'APP-2026-003', 3, 1, '2026-02-08 14:15:00', 'SHORTLISTED', 'ELIGIBLE', 'Authorized override for 1 backlog as student has 1 year relevant industry experience.', 1),
        (4, 'APP-2026-004', 4, 4, '2026-02-13 09:45:00', 'SELECTED', 'ELIGIBLE', 'Meets qualification, percentage (88%), 0 backlogs, and strong Data Analysis + Python profile.', 0),
        (5, 'APP-2026-005', 6, 1, '2026-02-04 15:00:00', 'JOINED', 'ELIGIBLE', 'Meets all academic criteria and proficient in Python, SQL, and AWS.', 0),
        (6, 'APP-2026-006', 7, 3, '2026-02-11 16:30:00', 'INTERVIEWED', 'ELIGIBLE', 'MCA 2025 graduate with 76% score.', 0)
    ]
    cursor.executemany("INSERT OR IGNORE INTO applications (application_id, application_code, candidate_id, job_id, applied_date, current_stage, eligibility_status, eligibility_remarks, is_override) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", apps_data)

    # Application History
    app_hist_data = [
        (1, 1, 'APPLIED', 'ELIGIBILITY_VERIFIED', 'Candidate criteria verified and confirmed eligible.', 2, '2026-02-02 10:30:00'),
        (2, 1, 'ELIGIBILITY_VERIFIED', 'SHORTLISTED', 'Resume shortlisted by recruiting panel.', 2, '2026-02-03 11:00:00'),
        (3, 1, 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'Technical & HR rounds scheduled.', 2, '2026-02-04 12:00:00'),
        (4, 1, 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'Completed technical round.', 2, '2026-02-07 16:00:00'),
        (5, 1, 'INTERVIEWED', 'SELECTED', 'Candidate demonstrated exceptional problem solving in Python.', 2, '2026-02-08 17:00:00'),
        (6, 1, 'SELECTED', 'OFFERED', 'Offer letter issued with 8.5 LPA package.', 3, '2026-02-10 10:00:00'),
        (7, 1, 'OFFERED', 'JOINED', 'Candidate joined TechNova Solutions as Associate Python Engineer.', 3, '2026-02-25 09:00:00'),
        (8, 2, 'APPLIED', 'ELIGIBILITY_VERIFIED', 'Verified against job requirements.', 2, '2026-02-06 14:00:00'),
        (9, 2, 'ELIGIBILITY_VERIFIED', 'SHORTLISTED', 'Shortlisted for Java assessment.', 2, '2026-02-07 10:00:00'),
        (10, 2, 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'Interview round 1 scheduled.', 2, '2026-02-08 11:00:00'),
        (11, 4, 'APPLIED', 'ELIGIBILITY_VERIFIED', 'Verified and confirmed eligible.', 2, '2026-02-13 11:00:00'),
        (12, 4, 'ELIGIBILITY_VERIFIED', 'SHORTLISTED', 'Directly shortlisted due to academic excellence.', 2, '2026-02-14 10:00:00'),
        (13, 4, 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'Technical round scheduled.', 2, '2026-02-15 14:00:00'),
        (14, 4, 'INTERVIEW_SCHEDULED', 'INTERVIEWED', 'Round completed with high praise.', 2, '2026-02-18 16:30:00'),
        (15, 4, 'INTERVIEWED', 'SELECTED', 'Recommended for hire by AI team.', 2, '2026-02-19 18:00:00'),
        (16, 5, 'APPLIED', 'SELECTED', 'Fast track interview process completed.', 2, '2026-02-09 17:00:00'),
        (17, 5, 'SELECTED', 'OFFERED', 'Offered 9.0 LPA.', 3, '2026-02-12 11:00:00'),
        (18, 5, 'OFFERED', 'JOINED', 'Candidate accepted and joined TechNova.', 3, '2026-02-28 09:30:00')
    ]
    cursor.executemany("INSERT OR IGNORE INTO application_history (history_id, application_id, old_stage, new_stage, remarks, changed_by, changed_at) VALUES (?, ?, ?, ?, ?, ?, ?);", app_hist_data)

    # Interview Rounds
    rounds_data = [
        (1, 1, 1, 'Technical Round 1', '2026-02-06', '14:00:00', 'Online', 'Harish Nair (Senior Dev)', 'https://meet.google.com/xyz-technova', 'COMPLETED', 2),
        (2, 1, 2, 'Managerial & HR Round', '2026-02-08', '11:00:00', 'Online', 'Sunita Rao (HR Head)', 'https://meet.google.com/abc-technova', 'COMPLETED', 2),
        (3, 2, 1, 'Technical Assessment', '2026-11-15', '10:30:00', 'Online', 'Gaurav K (Tech Lead)', 'https://meet.google.com/java-cloudzen', 'SCHEDULED', 2),
        (4, 4, 1, 'Data Science Deep Dive', '2026-02-18', '15:00:00', 'Online', 'Dr. Swati Sen (Chief Scientist)', 'https://meet.google.com/dataminds-ds', 'COMPLETED', 2),
        (5, 6, 1, 'Aptitude & Coding Round', '2026-02-14', '11:00:00', 'In-person', 'Interview Panel A', 'Seminar Hall 2, Placement Block', 'COMPLETED', 2),
        (6, 6, 2, 'System Design & FinTech', '2026-11-20', '14:00:00', 'Online', 'Rajiv Khurana (VP Tech)', 'https://meet.google.com/apex-interview', 'SCHEDULED', 2)
    ]
    cursor.executemany("INSERT OR IGNORE INTO interview_rounds (interview_id, application_id, round_number, round_name, scheduled_date, scheduled_time, interview_mode, interviewer_name, meeting_link_or_venue, status, scheduled_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", rounds_data)

    # Interview Feedback
    feedback_data = [
        (1, 1, 5, 4, 5, 5, 'NEXT_ROUND', 'Outstanding grasp of Python generator functions, algorithmic complexity, and SQL joins.', 2, '2026-02-06 15:30:00'),
        (2, 2, 4, 5, 4, 5, 'SELECTED', 'Excellent cultural fit, clear career vision, confident communication, and enthusiastic attitude.', 2, '2026-02-08 12:00:00'),
        (3, 4, 5, 4, 5, 5, 'SELECTED', 'Brilliant clarity on feature engineering, statistics, and machine learning model validation.', 2, '2026-02-18 16:30:00'),
        (4, 5, 4, 3, 4, 4, 'NEXT_ROUND', 'Solid coding fundamentals, needs slight improvement in edge case explanations.', 2, '2026-02-14 12:30:00')
    ]
    cursor.executemany("INSERT OR IGNORE INTO interview_feedback (feedback_id, interview_id, technical_rating, communication_rating, problem_solving_rating, overall_rating, recommendation, remarks, submitted_by, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", feedback_data)

    # Offers
    offers_data = [
        (1, 'OFF-2026-001', 1, 1, 1, 1, 'Associate Python Backend Engineer', 8.50, '2026-02-10', '2026-02-25', 'ACCEPTED', 'Standard employment terms, 15 days joining bonus, Bangalore location.', 3),
        (2, 'OFF-2026-002', 5, 6, 1, 1, 'Associate Python Backend Engineer', 9.00, '2026-02-12', '2026-02-28', 'ACCEPTED', 'Fast-track offer accepted with immediate joining.', 3),
        (3, 'OFF-2026-003', 4, 4, 4, 4, 'Junior Data & ML Analyst', 9.50, '2026-02-20', '2026-07-01', 'OFFERED', 'Offer letter sent via email; awaiting formal sign-off.', 3)
    ]
    cursor.executemany("INSERT OR IGNORE INTO offers (offer_id, offer_code, application_id, candidate_id, company_id, job_id, designation, package_lpa, offer_date, expected_joining_date, status, remarks, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", offers_data)

    # Placements
    placements_data = [
        (1, 'PLC-2026-001', 1, 1, 1, 1, 'Associate Python Backend Engineer', 8.50, '2026-02-25', '2026-02-25', 'JOINED', 'Candidate successfully reported to TechNova Bangalore office.', 3),
        (2, 'PLC-2026-002', 2, 6, 1, 1, 'Associate Python Backend Engineer', 9.00, '2026-02-28', '2026-02-28', 'JOINED', 'Joining confirmed with HR Sunita Rao.', 3)
    ]
    cursor.executemany("INSERT OR IGNORE INTO placements (placement_id, placement_code, offer_id, candidate_id, company_id, job_id, designation, final_package_lpa, expected_joining_date, actual_joining_date, joining_status, remarks, recorded_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", placements_data)

    # Activity Logs
    logs_data = [
        (1, 'admin', 'System', 'INITIALIZE', 'SYS-001', 'Recruitment & Placement Management System initialized with default master data.', '127.0.0.1', '2026-01-10 09:00:00'),
        (2, 'recruiter', 'Jobs', 'CREATE', 'JOB-2026-001', 'Created job opening: Associate Python Backend Engineer at TechNova Solutions.', '127.0.0.1', '2026-02-01 10:00:00'),
        (2, 'recruiter', 'Applications', 'CREATE', 'APP-2026-001', 'Candidate Aarav Sharma applied for Associate Python Backend Engineer.', '127.0.0.1', '2026-02-02 10:00:00'),
        (2, 'recruiter', 'Interviews', 'SCHEDULE', 'INT-1', 'Scheduled Technical Round 1 for Aarav Sharma.', '127.0.0.1', '2026-02-04 12:00:00'),
        (3, 'placement', 'Offers', 'CREATE', 'OFF-2026-001', 'Issued offer letter OFF-2026-001 to Aarav Sharma for 8.50 LPA.', '127.0.0.1', '2026-02-10 10:00:00'),
        (3, 'placement', 'Placements', 'JOIN_CONFIRM', 'PLC-2026-001', 'Confirmed joining for Aarav Sharma at TechNova Solutions.', '127.0.0.1', '2026-02-25 09:30:00')
    ]
    cursor.executemany("INSERT OR IGNORE INTO activity_logs (user_id, user_name, module, action, record_id, description, ip_address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);", logs_data)

    conn.commit()
    conn.close()
    print("[Init DB] SQLite database initialized successfully!")


def init_mysql():
    """Execute MySQL schema.sql and sample_data.sql against MySQL server."""
    if not HAS_MYSQL_CONNECTOR:
        print("[Init DB Error] mysql-connector-python is not installed.")
        return

    import mysql.connector

    print(f"[Init DB] Connecting to MySQL server at {Config.DB_HOST}:{Config.DB_PORT} as {Config.DB_USER}...")
    # Connect without database first
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        autocommit=True
    )
    cursor = conn.cursor()

    schema_file = PROJECT_ROOT / "sql" / "schema.sql"
    sample_file = PROJECT_ROOT / "sql" / "sample_data.sql"

    print(f"[Init DB] Executing MySQL schema: {schema_file.name}")
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    for statement in schema_sql.split(";"):
        stmt = statement.strip()
        if stmt:
            cursor.execute(stmt)

    print(f"[Init DB] Executing MySQL sample data: {sample_file.name}")
    with open(sample_file, "r", encoding="utf-8") as f:
        sample_sql = f.read()

    for statement in sample_sql.split(";"):
        stmt = statement.strip()
        if stmt:
            cursor.execute(stmt)

    cursor.close()
    conn.close()
    print("[Init DB] MySQL database initialized and seeded successfully!")


def main():
    engine = get_active_engine()
    if engine == "mysql":
        try:
            init_mysql()
        except Exception as e:
            print(f"[Init DB Error] Failed initializing MySQL: {e}")
            print("[Init DB] Falling back to initialize SQLite database for seamless operation...")
            init_sqlite()
    else:
        init_sqlite()


if __name__ == "__main__":
    main()

