"""
Recruitment & Placement Management System
Main Flask Application & Routing Controller
"""

import os
import secrets
from functools import wraps
from datetime import date, datetime, timedelta
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    abort
)

from config import Config
from dao.db import get_active_engine
from dao import (
    candidate_dao,
    company_dao,
    job_dao,
    application_dao,
    interview_dao,
    offer_dao,
    placement_dao,
    activity_dao,
    report_dao,
    user_dao
)
from services import (
    auth_service,
    candidate_service,
    company_service,
    job_service,
    eligibility_service,
    application_service,
    interview_service,
    offer_service,
    exceptions
)

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(Config)


# --------------------------------------------------------------------------
# Startup Database Integrity Verification
# --------------------------------------------------------------------------
def ensure_database_initialized():
    """Ensure database has tables and initial seed data if fresh."""
    engine = get_active_engine()
    if engine == "sqlite":
        from pathlib import Path
        db_file = Path(Config.SQLITE_DB_PATH)
        if not db_file.exists() or db_file.stat().st_size == 0:
            print("[Startup] Initializing SQLite database...")
            from sql.init_database import init_sqlite
            init_sqlite()


ensure_database_initialized()


# --------------------------------------------------------------------------
# Security & CSRF Helpers
# --------------------------------------------------------------------------
def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


@app.context_processor
def inject_template_globals():
    """Injects user session, role helpers, and CSRF token into all templates."""
    return {
        "current_user": session.get("username"),
        "current_role": session.get("role_name"),
        "user_full_name": session.get("full_name"),
        "csrf_token": generate_csrf_token,
        "now": datetime.now()
    }


@app.before_request
def csrf_protect():
    """Validates CSRF token on state-changing requests."""
    if request.method in ["POST", "PUT", "DELETE"]:
        # Allow json API or form token
        token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        expected = session.get("csrf_token")
        if not token or token != expected:
            # Skip only if unauthenticated login form where session token was just set
            if request.endpoint != "login":
                flash("Your security session expired or invalid form submission. Please retry.", "error")
                return redirect(request.referrer or url_for("dashboard"))


# --------------------------------------------------------------------------
# Role-Based Access Control Decorators
# --------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for("login"))
            user_role = session.get("role_name")
            if user_role not in allowed_roles:
                flash(f"Access Denied. '{user_role}' role is not authorized for this action.", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --------------------------------------------------------------------------
# Authentication Routes
# --------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        try:
            user = auth_service.authenticate_user(username, password)
            if user:
                session.clear()
                session["user_id"] = user["user_id"]
                session["username"] = user["username"]
                session["full_name"] = user["full_name"]
                session["role_name"] = user["role_name"]
                session["role_id"] = user["role_id"]
                generate_csrf_token()

                activity_dao.log_activity(
                    user_id=user["user_id"],
                    user_name=user["username"],
                    module="Auth",
                    action="LOGIN",
                    record_id=str(user["user_id"]),
                    description=f"User {user['username']} logged in successfully.",
                    ip_address=request.remote_addr
                )

                flash(f"Welcome back, {user['full_name']}!", "success")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("dashboard"))
            else:
                flash("Invalid username or password. Please try again.", "error")
        except exceptions.ValidationError as ve:
            flash(str(ve), "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    user_id = session.get("user_id")
    username = session.get("username")
    if user_id:
        activity_dao.log_activity(
            user_id=user_id,
            user_name=username,
            module="Auth",
            action="LOGOUT",
            record_id=str(user_id),
            description=f"User {username} logged out.",
            ip_address=request.remote_addr
        )
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    metrics = report_dao.get_dashboard_metrics()
    recent_activities = activity_dao.get_recent_activities(limit=8)
    return render_template(
        "dashboard.html",
        metrics=metrics,
        recent_activities=recent_activities
    )


# --------------------------------------------------------------------------
# Candidate Management
# --------------------------------------------------------------------------
@app.route("/candidates")
@login_required
def list_candidates():
    filters = {
        "search": request.args.get("search"),
        "technology": request.args.get("technology"),
        "qualification": request.args.get("qualification"),
        "passing_year": request.args.get("passing_year"),
        "profile_status": request.args.get("profile_status"),
        "placement_status": request.args.get("placement_status")
    }

    candidates = candidate_dao.search_candidates(
        search=filters["search"],
        technology=filters["technology"],
        qualification=filters["qualification"],
        passing_year=filters["passing_year"],
        profile_status=filters["profile_status"],
        placement_status=filters["placement_status"]
    )

    technologies = candidate_dao.execute_query(
        "SELECT DISTINCT primary_technology FROM candidates ORDER BY primary_technology ASC"
    )

    return render_template(
        "candidates/list.html",
        candidates=candidates,
        filters=filters,
        technologies=technologies
    )


@app.route("/candidates/new", methods=["GET"])
@login_required
@role_required(["Admin", "Placement Officer", "Recruiter"])
def create_candidate_screen():
    all_skills = candidate_dao.get_all_skills()
    import time
    default_code = f"CAND-2026-{str(int(time.time()) % 10000).zfill(4)}"
    return render_template(
        "candidates/form.html",
        is_edit=False,
        candidate=None,
        default_code=default_code,
        all_skills=all_skills,
        candidate_skill_ids=[],
        candidate_skill_profs={}
    )


@app.route("/candidates/new", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer", "Recruiter"])
def create_candidate_action():
    data = request.form.to_dict()

    # Extract skills
    skill_ids = request.form.getlist("skill_ids")
    skill_items = []
    for sk_id in skill_ids:
        try:
            sk_int = int(sk_id)
            prof = request.form.get(f"prof_{sk_id}", "Intermediate")
            skill_items.append((sk_int, prof))
        except ValueError:
            pass

    try:
        cand_id = candidate_service.create_candidate(
            data=data,
            skill_items=skill_items,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash(f"Candidate '{data.get('first_name')} {data.get('last_name')}' created successfully!", "success")
        return redirect(url_for("view_candidate_detail", candidate_id=cand_id))
    except (exceptions.ValidationError, exceptions.DuplicateError) as err:
        flash(str(err), "error")
        all_skills = candidate_dao.get_all_skills()
        return render_template(
            "candidates/form.html",
            is_edit=False,
            candidate=data,
            default_code=data.get("candidate_code"),
            all_skills=all_skills,
            candidate_skill_ids=[int(s) for s in skill_ids if s.isdigit()],
            candidate_skill_profs={int(s): request.form.get(f"prof_{s}", "Intermediate") for s in skill_ids if s.isdigit()}
        )


@app.route("/candidates/<int:candidate_id>")
@login_required
def view_candidate_detail(candidate_id):
    candidate = candidate_dao.get_candidate_by_id(candidate_id)
    if not candidate:
        flash("Candidate not found.", "error")
        return redirect(url_for("list_candidates"))

    applications = candidate_dao.get_candidate_applications(candidate_id)
    return render_template(
        "candidates/detail.html",
        candidate=candidate,
        applications=applications
    )


@app.route("/candidates/<int:candidate_id>/edit", methods=["GET"])
@login_required
@role_required(["Admin", "Placement Officer", "Recruiter"])
def edit_candidate_screen(candidate_id):
    candidate = candidate_dao.get_candidate_by_id(candidate_id)
    if not candidate:
        flash("Candidate not found.", "error")
        return redirect(url_for("list_candidates"))

    all_skills = candidate_dao.get_all_skills()
    candidate_skill_ids = [cs["skill_id"] for cs in candidate.get("skills", [])]
    candidate_skill_profs = {cs["skill_id"]: cs["proficiency_level"] for cs in candidate.get("skills", [])}

    return render_template(
        "candidates/form.html",
        is_edit=True,
        candidate=candidate,
        all_skills=all_skills,
        candidate_skill_ids=candidate_skill_ids,
        candidate_skill_profs=candidate_skill_profs
    )


@app.route("/candidates/<int:candidate_id>/edit", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer", "Recruiter"])
def edit_candidate_action(candidate_id):
    data = request.form.to_dict()

    skill_ids = request.form.getlist("skill_ids")
    skill_items = []
    for sk_id in skill_ids:
        try:
            sk_int = int(sk_id)
            prof = request.form.get(f"prof_{sk_id}", "Intermediate")
            skill_items.append((sk_int, prof))
        except ValueError:
            pass

    try:
        candidate_service.update_candidate(
            candidate_id=candidate_id,
            data=data,
            skill_items=skill_items,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Candidate profile updated successfully!", "success")
        return redirect(url_for("view_candidate_detail", candidate_id=candidate_id))
    except (exceptions.ValidationError, exceptions.DuplicateError, exceptions.NotFoundError) as err:
        flash(str(err), "error")
        return redirect(url_for("edit_candidate_screen", candidate_id=candidate_id))


@app.route("/candidates/<int:candidate_id>/deactivate", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer"])
def deactivate_candidate_action(candidate_id):
    try:
        candidate_service.deactivate_candidate(
            candidate_id=candidate_id,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Candidate has been deactivated. Historical records are preserved.", "info")
    except Exception as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("list_candidates"))


@app.route("/candidates/<int:candidate_id>/activate", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer"])
def activate_candidate_action(candidate_id):
    try:
        candidate_service.activate_candidate(
            candidate_id=candidate_id,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Candidate has been reactivated.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("list_candidates"))


# --------------------------------------------------------------------------
# Company Management
# --------------------------------------------------------------------------
@app.route("/companies")
@login_required
def list_companies():
    filters = {
        "search": request.args.get("search"),
        "industry": request.args.get("industry"),
        "status": request.args.get("status")
    }

    companies = company_dao.search_companies(
        search=filters["search"],
        industry=filters["industry"],
        status=filters["status"]
    )

    industries = company_dao.execute_query(
        "SELECT DISTINCT industry FROM companies ORDER BY industry ASC"
    )

    return render_template(
        "companies/list.html",
        companies=companies,
        filters=filters,
        industries=industries
    )


@app.route("/companies/new", methods=["GET"])
@login_required
@role_required(["Admin", "Placement Officer"])
def create_company_screen():
    import time
    default_code = f"COMP-{str(int(time.time()) % 1000).zfill(3)}"
    return render_template("companies/form.html", is_edit=False, company=None, default_code=default_code)


@app.route("/companies/new", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer"])
def create_company_action():
    data = request.form.to_dict()
    try:
        comp_id = company_service.create_company(
            data=data,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash(f"Company '{data.get('company_name')}' registered successfully!", "success")
        return redirect(url_for("view_company_detail", company_id=comp_id))
    except exceptions.ValidationError as err:
        flash(str(err), "error")
        return render_template("companies/form.html", is_edit=False, company=data, default_code=data.get("company_code"))


@app.route("/companies/<int:company_id>")
@login_required
def view_company_detail(company_id):
    company = company_dao.get_company_by_id(company_id)
    if not company:
        flash("Company not found.", "error")
        return redirect(url_for("list_companies"))

    jobs = company_dao.get_company_jobs(company_id)
    return render_template("companies/detail.html", company=company, jobs=jobs)


@app.route("/companies/<int:company_id>/edit", methods=["GET"])
@login_required
@role_required(["Admin", "Placement Officer"])
def edit_company_screen(company_id):
    company = company_dao.get_company_by_id(company_id)
    if not company:
        flash("Company not found.", "error")
        return redirect(url_for("list_companies"))

    return render_template("companies/form.html", is_edit=True, company=company)


@app.route("/companies/<int:company_id>/edit", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer"])
def edit_company_action(company_id):
    data = request.form.to_dict()
    try:
        company_service.update_company(
            company_id=company_id,
            data=data,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Company updated successfully!", "success")
        return redirect(url_for("view_company_detail", company_id=company_id))
    except (exceptions.ValidationError, exceptions.NotFoundError) as err:
        flash(str(err), "error")
        return redirect(url_for("edit_company_screen", company_id=company_id))


@app.route("/companies/<int:company_id>/deactivate", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer"])
def deactivate_company_action(company_id):
    try:
        company_service.deactivate_company(
            company_id=company_id,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Company deactivated. Associated jobs and placements are preserved.", "info")
    except Exception as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("list_companies"))


@app.route("/companies/<int:company_id>/activate", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer"])
def activate_company_action(company_id):
    try:
        company_service.activate_company(
            company_id=company_id,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Company reactivated successfully.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("list_companies"))


# --------------------------------------------------------------------------
# Job Management
# --------------------------------------------------------------------------
@app.route("/jobs")
@login_required
def list_jobs():
    filters = {
        "search": request.args.get("search"),
        "company_id": request.args.get("company_id"),
        "status": request.args.get("status"),
        "employment_type": request.args.get("employment_type")
    }

    jobs = job_dao.search_jobs(
        search=filters["search"],
        company_id=filters["company_id"],
        status=filters["status"],
        employment_type=filters["employment_type"]
    )

    companies = company_dao.get_active_companies()

    return render_template(
        "jobs/list.html",
        jobs=jobs,
        filters=filters,
        companies=companies
    )


@app.route("/jobs/new", methods=["GET"])
@login_required
@role_required(["Admin", "Recruiter", "Placement Officer"])
def create_job_screen():
    companies = company_dao.get_active_companies()
    all_skills = candidate_dao.get_all_skills()

    import time
    default_code = f"JOB-2026-{str(int(time.time()) % 1000).zfill(3)}"
    today = date.today().strftime("%Y-%m-%d")
    deadline = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")

    selected_comp_id = request.args.get("company_id", "")

    return render_template(
        "jobs/form.html",
        is_edit=False,
        job=None,
        default_code=default_code,
        companies=companies,
        all_skills=all_skills,
        job_skill_ids=[],
        job_skill_mandatory={},
        job_skill_profs={},
        default_posted_date=today,
        default_deadline=deadline,
        selected_company_id=selected_comp_id
    )


@app.route("/jobs/new", methods=["POST"])
@login_required
@role_required(["Admin", "Recruiter", "Placement Officer"])
def create_job_action():
    data = request.form.to_dict()

    skill_ids = request.form.getlist("skill_ids")
    skill_reqs = []
    for sk_id in skill_ids:
        try:
            sk_int = int(sk_id)
            is_mand = 1 if request.form.get(f"mandatory_{sk_id}") == "1" else 0
            min_prof = request.form.get(f"prof_{sk_id}", "Intermediate")
            skill_reqs.append((sk_int, is_mand, min_prof))
        except ValueError:
            pass

    try:
        job_id = job_service.create_job(
            data=data,
            skill_requirements=skill_reqs,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash(f"Job opening '{data.get('title')}' created successfully!", "success")
        return redirect(url_for("view_job_detail", job_id=job_id))
    except exceptions.ValidationError as err:
        flash(str(err), "error")
        companies = company_dao.get_active_companies()
        all_skills = candidate_dao.get_all_skills()
        return render_template(
            "jobs/form.html",
            is_edit=False,
            job=data,
            default_code=data.get("job_code"),
            companies=companies,
            all_skills=all_skills,
            job_skill_ids=[int(s) for s in skill_ids if s.isdigit()],
            job_skill_mandatory={int(s): (1 if request.form.get(f"mandatory_{s}") == "1" else 0) for s in skill_ids if s.isdigit()},
            job_skill_profs={int(s): request.form.get(f"prof_{s}", "Intermediate") for s in skill_ids if s.isdigit()},
            default_posted_date=data.get("posted_date"),
            default_deadline=data.get("deadline")
        )


@app.route("/jobs/<int:job_id>")
@login_required
def view_job_detail(job_id):
    job = job_dao.get_job_by_id(job_id)
    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("list_jobs"))

    applications = application_dao.search_applications(job_id=job_id)

    # Check expired deadline
    from datetime import date, datetime
    today = date.today()
    deadline = job.get("deadline")
    if isinstance(deadline, str):
        deadline = datetime.strptime(deadline[:10], "%Y-%m-%d").date()
    is_expired = bool(deadline and deadline < today)

    return render_template(
        "jobs/detail.html",
        job=job,
        applications=applications,
        is_expired=is_expired
    )


@app.route("/jobs/<int:job_id>/edit", methods=["GET"])
@login_required
@role_required(["Admin", "Recruiter", "Placement Officer"])
def edit_job_screen(job_id):
    job = job_dao.get_job_by_id(job_id)
    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("list_jobs"))

    companies = company_dao.get_active_companies()
    all_skills = candidate_dao.get_all_skills()

    job_skill_ids = [js["skill_id"] for js in job.get("skills", [])]
    job_skill_mandatory = {js["skill_id"]: js["is_mandatory"] for js in job.get("skills", [])}
    job_skill_profs = {js["skill_id"]: js["min_proficiency"] for js in job.get("skills", [])}

    return render_template(
        "jobs/form.html",
        is_edit=True,
        job=job,
        companies=companies,
        all_skills=all_skills,
        job_skill_ids=job_skill_ids,
        job_skill_mandatory=job_skill_mandatory,
        job_skill_profs=job_skill_profs
    )


@app.route("/jobs/<int:job_id>/edit", methods=["POST"])
@login_required
@role_required(["Admin", "Recruiter", "Placement Officer"])
def edit_job_action(job_id):
    data = request.form.to_dict()

    skill_ids = request.form.getlist("skill_ids")
    skill_reqs = []
    for sk_id in skill_ids:
        try:
            sk_int = int(sk_id)
            is_mand = 1 if request.form.get(f"mandatory_{sk_id}") == "1" else 0
            min_prof = request.form.get(f"prof_{sk_id}", "Intermediate")
            skill_reqs.append((sk_int, is_mand, min_prof))
        except ValueError:
            pass

    try:
        job_service.update_job(
            job_id=job_id,
            data=data,
            skill_requirements=skill_reqs,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Job updated successfully!", "success")
        return redirect(url_for("view_job_detail", job_id=job_id))
    except (exceptions.ValidationError, exceptions.NotFoundError) as err:
        flash(str(err), "error")
        return redirect(url_for("edit_job_screen", job_id=job_id))


@app.route("/jobs/<int:job_id>/status", methods=["POST"])
@login_required
@role_required(["Admin", "Recruiter", "Placement Officer"])
def change_job_status_action(job_id):
    new_status = request.form.get("status")
    try:
        job_service.change_job_status(
            job_id=job_id,
            new_status=new_status,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash(f"Job status changed to {new_status}.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("view_job_detail", job_id=job_id))


# --------------------------------------------------------------------------
# Eligibility Checks & Applications
# --------------------------------------------------------------------------
@app.route("/applications")
@login_required
def list_applications():
    filters = {
        "search": request.args.get("search"),
        "job_id": request.args.get("job_id"),
        "stage": request.args.get("stage"),
        "eligibility": request.args.get("eligibility")
    }

    applications = application_dao.search_applications(
        search=filters["search"],
        job_id=filters["job_id"],
        stage=filters["stage"],
        eligibility=filters["eligibility"]
    )

    jobs = job_dao.execute_query("""
        SELECT j.job_id, j.title, c.company_name
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY j.job_id DESC
    """)

    from models.application import ApplicationStage
    stages = ApplicationStage.ALL_STAGES

    return render_template(
        "applications/list.html",
        applications=applications,
        filters=filters,
        jobs=jobs,
        stages=stages
    )


@app.route("/api/check-eligibility")
@login_required
def check_eligibility_api():
    """Returns JSON evaluation of a candidate against a job."""
    cand_id = request.args.get("candidate_id")
    job_id = request.args.get("job_id")

    if not cand_id or not job_id:
        return jsonify({"success": False, "message": "Candidate ID and Job ID are required."}), 400

    try:
        cand_int = int(cand_id)
        job_int = int(job_id)
        result = eligibility_service.evaluate_eligibility(cand_int, job_int)
        return jsonify({
            "success": True,
            "is_eligible": result.is_eligible,
            "status": result.status,
            "reasons": result.reasons
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/applications/apply", methods=["GET"])
@login_required
def apply_job_screen():
    candidates = candidate_dao.execute_query(
        "SELECT candidate_id, candidate_code, first_name, last_name, qualification, passing_year, percentage, primary_technology FROM candidates WHERE profile_status = 'Active' ORDER BY first_name ASC"
    )
    jobs = job_dao.get_open_jobs()

    selected_cand_id = request.args.get("candidate_id", "")
    selected_job_id = request.args.get("job_id", "")

    return render_template(
        "applications/apply.html",
        candidates=candidates,
        jobs=jobs,
        selected_candidate_id=selected_cand_id,
        selected_job_id=selected_job_id
    )


@app.route("/applications/apply", methods=["POST"])
@login_required
def submit_application_action():
    try:
        candidate_id = int(request.form.get("candidate_id", 0))
        job_id = int(request.form.get("job_id", 0))
    except (ValueError, TypeError):
        flash("Please select both a valid candidate and a job opening.", "error")
        return redirect(url_for("apply_job_screen"))

    is_override = bool(request.form.get("is_override") == "1")
    override_reason = request.form.get("override_reason", "").strip()

    try:
        app_id = application_service.submit_application(
            candidate_id=candidate_id,
            job_id=job_id,
            is_override=is_override,
            override_reason=override_reason,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Application successfully recorded!", "success")
        return redirect(url_for("view_application_detail", application_id=app_id))
    except (exceptions.EligibilityError, exceptions.DuplicateError, exceptions.ValidationError, exceptions.NotFoundError) as err:
        flash(str(err), "error")
        return redirect(url_for("apply_job_screen", candidate_id=candidate_id, job_id=job_id))


@app.route("/applications/<int:application_id>")
@login_required
def view_application_detail(application_id):
    app_data = application_dao.get_application_by_id(application_id)
    if not app_data:
        flash("Application not found.", "error")
        return redirect(url_for("list_applications"))

    history = application_dao.get_application_history(application_id)
    interviews = interview_dao.get_interviews_by_application(application_id)
    offer = offer_dao.get_offer_by_application_id(application_id)
    placement = placement_dao.get_placement_by_offer_id(offer["offer_id"]) if offer else None

    from models.application import ApplicationStage
    current_stage = app_data["current_stage"]
    allowed_next_stages = ApplicationStage.TRANSITIONS.get(current_stage, [])

    return render_template(
        "applications/detail.html",
        app=app_data,
        history=history,
        interviews=interviews,
        offer=offer,
        placement=placement,
        allowed_next_stages=allowed_next_stages
    )


@app.route("/applications/<int:application_id>/transition", methods=["POST"])
@login_required
@role_required(["Admin", "Recruiter", "Placement Officer"])
def transition_application_stage_action(application_id):
    new_stage = request.form.get("new_stage", "").strip()
    remarks = request.form.get("remarks", "").strip()

    try:
        application_service.transition_stage(
            application_id=application_id,
            new_stage=new_stage,
            remarks=remarks,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash(f"Application transitioned to '{new_stage}' successfully.", "success")
    except (exceptions.StateTransitionError, exceptions.ValidationError, exceptions.NotFoundError) as err:
        flash(str(err), "error")

    return redirect(url_for("view_application_detail", application_id=application_id))


# --------------------------------------------------------------------------
# Interview Rounds & Feedback
# --------------------------------------------------------------------------
@app.route("/interviews")
@login_required
def list_interviews():
    filters = {
        "search": request.args.get("search"),
        "status": request.args.get("status"),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to")
    }

    interviews = interview_dao.search_interviews(
        search=filters["search"],
        status=filters["status"],
        date_from=filters["date_from"],
        date_to=filters["date_to"]
    )

    return render_template("interviews/list.html", interviews=interviews, filters=filters)


@app.route("/interviews/schedule", methods=["GET"])
@login_required
@role_required(["Admin", "Recruiter"])
def schedule_interview_screen():
    applications = application_dao.execute_query("""
        SELECT a.application_id, a.application_code, a.current_stage,
               c.first_name, c.last_name, c.candidate_code,
               j.title AS job_title, comp.company_name
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies comp ON j.company_id = comp.company_id
        WHERE a.current_stage IN ('SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED')
        ORDER BY a.application_id DESC
    """)

    selected_app_id = request.args.get("application_id", "")
    default_round_num = 1
    if selected_app_id and selected_app_id.isdigit():
        ex = interview_dao.get_interviews_by_application(int(selected_app_id))
        default_round_num = len(ex) + 1

    today = date.today().strftime("%Y-%m-%d")

    return render_template(
        "interviews/schedule.html",
        applications=applications,
        selected_application_id=selected_app_id,
        default_round_num=default_round_num,
        default_date=today
    )


@app.route("/interviews/schedule", methods=["POST"])
@login_required
@role_required(["Admin", "Recruiter"])
def schedule_interview_action():
    data = request.form.to_dict()
    try:
        intv_id = interview_service.schedule_interview_round(
            data=data,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Interview round scheduled successfully!", "success")
        return redirect(url_for("list_interviews"))
    except (exceptions.ValidationError, exceptions.NotFoundError) as err:
        flash(str(err), "error")
        return redirect(url_for("schedule_interview_screen", application_id=data.get("application_id")))


@app.route("/interviews/<int:interview_id>/feedback", methods=["GET"])
@login_required
@role_required(["Admin", "Recruiter", "Placement Officer"])
def record_feedback_screen(interview_id):
    interview = interview_dao.get_interview_by_id(interview_id)
    if not interview:
        flash("Interview round not found.", "error")
        return redirect(url_for("list_interviews"))

    if interview.get("feedback"):
        flash("Feedback has already been recorded for this interview round.", "info")
        return redirect(url_for("view_application_detail", application_id=interview["application_id"]))

    return render_template("interviews/feedback.html", interview=interview)


@app.route("/interviews/<int:interview_id>/feedback", methods=["POST"])
@login_required
@role_required(["Admin", "Recruiter", "Placement Officer"])
def record_feedback_action(interview_id):
    data = request.form.to_dict()
    data["interview_id"] = interview_id
    try:
        interview_service.submit_interview_feedback(
            data=data,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Interview feedback recorded successfully! Candidate stage updated.", "success")
        interview = interview_dao.get_interview_by_id(interview_id)
        return redirect(url_for("view_application_detail", application_id=interview["application_id"]))
    except (exceptions.ValidationError, exceptions.DuplicateError, exceptions.NotFoundError) as err:
        flash(str(err), "error")
        return redirect(url_for("record_feedback_screen", interview_id=interview_id))


@app.route("/interviews/<int:interview_id>/reschedule", methods=["GET", "POST"])
@login_required
@role_required(["Admin", "Recruiter"])
def reschedule_interview_screen(interview_id):
    interview = interview_dao.get_interview_by_id(interview_id)
    if not interview:
        flash("Interview round not found.", "error")
        return redirect(url_for("list_interviews"))

    if request.method == "POST":
        new_date = request.form.get("scheduled_date")
        new_time = request.form.get("scheduled_time")
        venue = request.form.get("meeting_link_or_venue")
        try:
            interview_service.reschedule_interview_round(
                interview_id=interview_id,
                new_date=new_date,
                new_time=new_time,
                link_or_venue=venue,
                user_id=session.get("user_id"),
                user_name=session.get("username")
            )
            flash("Interview rescheduled successfully.", "success")
            return redirect(url_for("list_interviews"))
        except exceptions.ValidationError as err:
            flash(str(err), "error")

    return render_template("interviews/reschedule.html", interview=interview)


@app.route("/interviews/<int:interview_id>/status", methods=["POST"])
@login_required
@role_required(["Admin", "Recruiter"])
def change_interview_status_action(interview_id):
    new_status = request.form.get("status", "NO_SHOW")
    try:
        interview_service.update_interview_status(
            interview_id=interview_id,
            new_status=new_status,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash(f"Interview marked as {new_status}.", "info")
    except Exception as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("list_interviews"))


# --------------------------------------------------------------------------
# Job Offers & Placements
# --------------------------------------------------------------------------
@app.route("/offers")
@login_required
def list_offers():
    filters = {
        "search": request.args.get("search"),
        "status": request.args.get("status"),
        "company_id": request.args.get("company_id")
    }

    offers = offer_dao.search_offers(
        search=filters["search"],
        status=filters["status"],
        company_id=filters["company_id"]
    )

    companies = company_dao.get_active_companies()
    return render_template("offers/list.html", offers=offers, filters=filters, companies=companies)


@app.route("/offers/new", methods=["GET"])
@login_required
@role_required(["Admin", "Placement Officer"])
def create_offer_screen():
    selected_applications = application_dao.execute_query("""
        SELECT a.application_id, a.application_code, a.candidate_id, a.job_id,
               c.first_name, c.last_name, c.candidate_code,
               j.title AS job_title, j.min_package, j.max_package,
               comp.company_id, comp.company_name
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies comp ON j.company_id = comp.company_id
        WHERE a.current_stage IN ('SELECTED', 'INTERVIEWED')
          AND NOT EXISTS (SELECT 1 FROM offers o WHERE o.application_id = a.application_id)
        ORDER BY a.application_id DESC
    """)

    selected_app_id = request.args.get("application_id", "")
    default_designation = ""
    default_package = 8.00

    if selected_app_id and selected_app_id.isdigit():
        for sa in selected_applications:
            if str(sa["application_id"]) == selected_app_id:
                default_designation = sa["job_title"]
                default_package = sa["min_package"]
                break

    today = date.today().strftime("%Y-%m-%d")
    joining_date = (date.today() + timedelta(days=15)).strftime("%Y-%m-%d")

    return render_template(
        "offers/create.html",
        selected_applications=selected_applications,
        selected_application_id=selected_app_id,
        default_designation=default_designation,
        default_package=default_package,
        default_offer_date=today,
        default_joining_date=joining_date
    )


@app.route("/offers/new", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer"])
def create_offer_action():
    data = request.form.to_dict()
    try:
        offer_id = offer_service.create_offer(
            data=data,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Job offer letter issued successfully!", "success")
        return redirect(url_for("list_offers"))
    except (exceptions.ValidationError, exceptions.DuplicateError, exceptions.StateTransitionError, exceptions.NotFoundError) as err:
        flash(str(err), "error")
        return redirect(url_for("create_offer_screen", application_id=data.get("application_id")))


@app.route("/offers/<int:offer_id>/status", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer"])
def update_offer_status_action(offer_id):
    new_status = request.form.get("status")
    remarks = request.form.get("remarks")
    try:
        offer_service.update_offer_status(
            offer_id=offer_id,
            new_status=new_status,
            remarks=remarks,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash(f"Offer status changed to {new_status}.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("list_offers"))


@app.route("/placements")
@login_required
def list_placements():
    filters = {
        "search": request.args.get("search"),
        "joining_status": request.args.get("joining_status"),
        "company_id": request.args.get("company_id")
    }

    placements = placement_dao.search_placements(
        search=filters["search"],
        joining_status=filters["joining_status"],
        company_id=filters["company_id"]
    )

    companies = company_dao.get_active_companies()
    return render_template("offers/placements_list.html", placements=placements, filters=filters, companies=companies)


@app.route("/placements/new", methods=["GET"])
@login_required
@role_required(["Admin", "Placement Officer"])
def record_placement_screen():
    offer_id = request.args.get("offer_id")
    if not offer_id:
        flash("Offer selection is required to record placement.", "error")
        return redirect(url_for("list_offers"))

    offer = offer_dao.get_offer_by_id(int(offer_id))
    if not offer:
        flash("Offer not found.", "error")
        return redirect(url_for("list_offers"))

    today = date.today().strftime("%Y-%m-%d")

    return render_template(
        "offers/placement.html",
        offer=offer,
        default_actual_date=today
    )


@app.route("/placements/new", methods=["POST"])
@login_required
@role_required(["Admin", "Placement Officer"])
def record_placement_action():
    offer_id = request.args.get("offer_id")
    data = request.form.to_dict()
    data["offer_id"] = int(offer_id) if offer_id else int(request.form.get("offer_id", 0))

    try:
        plc_id = offer_service.record_placement(
            data=data,
            user_id=session.get("user_id"),
            user_name=session.get("username")
        )
        flash("Placement and joining outcome confirmed successfully!", "success")
        return redirect(url_for("list_placements"))
    except (exceptions.ValidationError, exceptions.DuplicateError, exceptions.NotFoundError) as err:
        flash(str(err), "error")
        return redirect(url_for("record_placement_screen", offer_id=offer_id))


# --------------------------------------------------------------------------
# Reports & Analytics Hub
# --------------------------------------------------------------------------
@app.route("/reports")
@login_required
def reports_hub():
    passing_year = request.args.get("passing_year")

    # 1. Candidates by tech
    tech_report = report_dao.report_candidates_by_technology(passing_year=passing_year)

    # 2. Open jobs by company
    open_jobs = report_dao.report_open_jobs_by_company()

    # 3. Applications by status
    app_status = report_dao.report_applications_by_status()

    # 4. Recruitment Funnel
    funnel = report_dao.report_recruitment_funnel()

    # 5. Company-wise placements
    company_placements = report_dao.report_company_wise_placements()

    # 6. Technology-wise placements
    tech_placements = report_dao.report_technology_wise_placements()

    # 7. Recruiter Performance
    recruiter_perf = report_dao.report_recruiter_performance()

    # 8. Pending & upcoming interviews
    upcoming_intvs = report_dao.report_pending_upcoming_interviews()

    # 9. Offer to joining conversion
    conv = report_dao.report_offer_to_joining_conversion()

    # 10. Open job aging
    job_aging = report_dao.report_open_job_aging()

    # 11. Placed vs unplaced
    placed_ratio = report_dao.report_placed_vs_unplaced()

    return render_template(
        "reports/index.html",
        tech_report=tech_report,
        open_jobs=open_jobs,
        app_status=app_status,
        funnel=funnel,
        company_placements=company_placements,
        tech_placements=tech_placements,
        recruiter_perf=recruiter_perf,
        upcoming_intvs=upcoming_intvs,
        conv=conv,
        job_aging=job_aging,
        placed_ratio=placed_ratio
    )


# --------------------------------------------------------------------------
# Activity Logs
# --------------------------------------------------------------------------
@app.route("/activity-logs")
@login_required
@role_required(["Admin", "Placement Officer"])
def view_activity_logs():
    filters = {
        "module": request.args.get("module"),
        "search": request.args.get("search")
    }

    logs = activity_dao.search_activity_logs(
        module=filters["module"],
        search=filters["search"],
        limit=100
    )

    return render_template("activity_logs.html", logs=logs, filters=filters)


# --------------------------------------------------------------------------
# Error Handlers
# --------------------------------------------------------------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template("base.html"), 404


@app.errorhandler(403)
def forbidden_error(error):
    flash("Access forbidden: you do not possess the required permissions.", "error")
    return redirect(url_for("dashboard"))


@app.errorhandler(500)
def internal_error(error):
    return render_template("base.html"), 500


# --------------------------------------------------------------------------
# App Entry Point
# --------------------------------------------------------------------------
if __name__ == "__main__":
    port = Config.PORT
    debug = Config.DEBUG
    print(f"Starting Recruitment & Placement Management System on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)

