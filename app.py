import os
import sys
from datetime import datetime, date, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, abort
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError
from werkzeug.exceptions import HTTPException

from config import Config, get_db
from models.user_model import (
    create_user,
    find_by_email,
    find_by_id,
    verify_user_password,
    update_profile,
    update_role,
    get_all_users,
    count_admins,
    init_user_indexes,
    ALLOWED_ROLES
)
from models.crime_model import (
    create_crime,
    get_crime_by_id,
    update_crime,
    delete_crime as db_delete_crime,
    search_crimes,
    get_dashboard_stats,
    seed_sample_crimes,
    init_crime_indexes,
    ALLOWED_CRIME_TYPES,
    ALLOWED_CASE_STATUSES
)
from utils.helpers import (
    login_required,
    admin_required,
    officer_required,
    generate_csrf_token,
    validate_csrf_token,
    parse_object_id,
    validate_email,
    format_datetime,
    format_date
)

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Register custom Jinja2 template filters
app.jinja_env.filters["format_datetime"] = format_datetime
app.jinja_env.filters["format_date"] = format_date


def get_current_db():
    """
    Get or create a cached database connection for the current request.
    Gracefully handles connection failures.
    """
    if "db" not in g:
        try:
            g.db = get_db()
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            app.logger.error(f"Database connection error: {e}")
            abort(500)
    return g.db


@app.context_processor
def inject_global_template_context():
    """Inject CSRF token and enum options into all Jinja2 templates."""
    return {
        "csrf_token": generate_csrf_token,
        "crime_types": ALLOWED_CRIME_TYPES,
        "case_statuses": ALLOWED_CASE_STATUSES,
        "today": date.today().isoformat(),
        "current_year": datetime.now().year
    }


@app.before_request
def csrf_protect_and_init():
    """
    Validate CSRF token for all state-changing HTTP requests.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        # Retrieve token from form or header
        token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        if not token or not validate_csrf_token(token):
            flash("Security check failed (Invalid or missing CSRF token). Please try submitting again.", "danger")
            return redirect(request.referrer or url_for("index"))


# ============================================================================
# GENERAL & AUTHENTICATION ROUTES
# ============================================================================

@app.route("/")
def index():
    """Public landing page and project introduction."""
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Personnel account registration."""
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        department = request.form.get("department", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Server-side validation
        if not full_name or not email or not department or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if not validate_email(email):
            flash("Please enter a valid department email address.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        db = get_current_db()
        try:
            # All self-registered accounts default to 'Viewer' role
            create_user(db, full_name, email, password, department, role="Viewer")
            flash("Registration successful. You may now log in to the portal.", "success")
            return redirect(url_for("login"))
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("register.html")
        except DuplicateKeyError:
            flash("An account with this email address already exists.", "danger")
            return render_template("register.html")
        except Exception as e:
            app.logger.error(f"Registration failure: {e}")
            flash("An unexpected error occurred during registration. Please try again.", "danger")
            return render_template("register.html")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Personnel authentication with Flask sessions."""
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please provide both email and password.", "danger")
            return render_template("login.html")

        db = get_current_db()
        user = find_by_email(db, email)

        if not user or not verify_user_password(user.get("password_hash"), password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        # Create session
        session.clear()
        session["user_id"] = str(user["_id"])
        session["user_name"] = user.get("full_name", "Personnel")
        session["email"] = user.get("email")
        session["role"] = user.get("role", "Viewer")
        session.permanent = True

        flash(f"Welcome back, {session['user_name']}.", "success")
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    """Clear Flask session and redirect to login."""
    session.clear()
    flash("You have been safely logged out.", "info")
    return redirect(url_for("login"))


# ============================================================================
# DASHBOARD ROUTE
# ============================================================================

@app.route("/dashboard")
@login_required
def dashboard():
    """Analytical crime intelligence dashboard with MongoDB aggregations."""
    db = get_current_db()
    stats = get_dashboard_stats(db)
    return render_template("dashboard.html", stats=stats)


# ============================================================================
# CRIME RECORD MANAGEMENT ROUTES
# ============================================================================

@app.route("/crimes")
@login_required
def view_crimes():
    """Display all crime records with multi-parameter search and filters."""
    db = get_current_db()
    q = request.args.get("q")
    crime_type = request.args.get("crime_type")
    case_status = request.args.get("case_status")
    location = request.args.get("location")
    case_number = request.args.get("case_number")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    crimes = search_crimes(
        db,
        query=q,
        crime_type=crime_type,
        case_status=case_status,
        location=location,
        case_number=case_number,
        date_from=date_from,
        date_to=date_to
    )

    return render_template("crimes.html", crimes=crimes)


@app.route("/crimes/add", methods=["GET", "POST"])
@login_required
@officer_required
def add_crime():
    """Create and save a new crime record."""
    db = get_current_db()
    if request.method == "POST":
        try:
            created_crime = create_crime(
                db,
                form_data=request.form,
                created_by_id=session.get("user_id")
            )
            flash(f"Crime record {created_crime['case_number']} added successfully.", "success")
            return redirect(url_for("crime_details", crime_id=created_crime["_id"]))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            app.logger.error(f"Error creating crime record: {e}")
            flash("Failed to save crime record due to a server error.", "danger")

    return render_template("add_crime.html")


@app.route("/crimes/<crime_id>")
@login_required
def crime_details(crime_id):
    """View complete incident details and dossier for a specific crime."""
    db = get_current_db()
    crime = get_crime_by_id(db, crime_id)
    if not crime:
        flash("The requested crime record does not exist or has an invalid identifier.", "danger")
        return redirect(url_for("view_crimes"))

    return render_template("crime_details.html", crime=crime)


@app.route("/crimes/edit/<crime_id>", methods=["GET", "POST"])
@login_required
@officer_required
def edit_crime(crime_id):
    """Edit existing crime record while preserving case number and created timestamp."""
    db = get_current_db()
    crime = get_crime_by_id(db, crime_id)
    if not crime:
        flash("Crime record not found.", "danger")
        return redirect(url_for("view_crimes"))

    if request.method == "POST":
        try:
            update_crime(db, crime_id, request.form)
            flash(f"Crime record {crime.get('case_number')} updated successfully.", "success")
            return redirect(url_for("crime_details", crime_id=crime_id))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            app.logger.error(f"Error updating crime record {crime_id}: {e}")
            flash("Failed to update record due to an unexpected error.", "danger")

    return render_template("edit_crime.html", crime=crime)


@app.route("/crimes/delete/<crime_id>", methods=["POST"])
@login_required
@admin_required
def delete_crime(crime_id):
    """Permanently delete a crime record (restricted strictly to Admins)."""
    db = get_current_db()
    try:
        db_delete_crime(db, crime_id)
        flash("Crime record deleted successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        app.logger.error(f"Error deleting crime record {crime_id}: {e}")
        flash("Unable to delete crime record.", "danger")

    return redirect(url_for("view_crimes"))


# ============================================================================
# USER PROFILE & ADMINISTRATIVE MANAGEMENT
# ============================================================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and update personnel profile."""
    db = get_current_db()
    user = find_by_id(db, session["user_id"])
    if not user:
        session.clear()
        flash("User session expired or user no longer exists.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        department = request.form.get("department", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not full_name:
            flash("Full name cannot be blank.", "danger")
            return render_template("profile.html", user=user)

        if new_password:
            if len(new_password) < 6:
                flash("New password must be at least 6 characters long.", "danger")
                return render_template("profile.html", user=user)
            if new_password != confirm_password:
                flash("New password and confirmation do not match.", "danger")
                return render_template("profile.html", user=user)

        try:
            update_profile(
                db,
                session["user_id"],
                full_name=full_name,
                department=department,
                new_password=new_password if new_password else None
            )
            session["user_name"] = full_name
            flash("Profile updated successfully.", "success")
            return redirect(url_for("profile"))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            app.logger.error(f"Error updating profile: {e}")
            flash("Could not update profile.", "danger")

    return render_template("profile.html", user=user)


@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    """Administrative user management panel to audit accounts and assign roles."""
    db = get_current_db()
    users = get_all_users(db)
    return render_template("admin_users.html", users=users)


@app.route("/admin/users/<user_id>/role", methods=["POST"])
@login_required
@admin_required
def update_user_role(user_id):
    """Update authorization role of a personnel account."""
    new_role = request.form.get("role", "").strip()
    db = get_current_db()
    try:
        update_role(db, user_id, new_role)
        flash("User role updated successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        app.logger.error(f"Error changing user role: {e}")
        flash("Failed to update user role.", "danger")

    return redirect(url_for("admin_users"))


# ============================================================================
# ERROR HANDLING
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """Custom friendly 404 page."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    """Custom friendly 500 page without leaking raw stack trace."""
    return render_template("500.html"), 500


@app.errorhandler(Exception)
def unhandled_exception(e):
    """Catch-all unhandled exceptions and present friendly 500 page."""
    if isinstance(e, HTTPException):
        return e
    app.logger.error(f"Unhandled exception: {e}", exc_info=True)
    return render_template("500.html"), 500


# ============================================================================
# CLI & INITIALIZATION COMMANDS
# ============================================================================

def run_init_admin():
    """Execute administrator initialization logic."""
    admin_email = os.getenv("ADMIN_EMAIL", "admin@crimerecord.local").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "AdminPass123!")
    admin_name = os.getenv("ADMIN_NAME", "Chief Administrator")
    admin_dept = os.getenv("ADMIN_DEPARTMENT", "Headquarters Administration")

    try:
        db = get_db()
        init_user_indexes(db)
        init_crime_indexes(db)

        existing = find_by_email(db, admin_email)
        if existing:
            if existing.get("role") != "Admin":
                update_role(db, existing["_id"], "Admin")
                print(f"[CRMS] Existing user '{admin_email}' promoted to Administrator.")
            else:
                print(f"[CRMS] Administrator '{admin_email}' is already configured.")
            return

        create_user(
            db,
            full_name=admin_name,
            email=admin_email,
            password=admin_password,
            department=admin_dept,
            role="Admin"
        )
        print(f"[CRMS] Administrator account created successfully:")
        print(f"       Email: {admin_email}")
        print(f"       Role:  Admin")
        print(f"       Department: {admin_dept}")
    except Exception as err:
        print(f"[CRMS ERROR] Could not initialize administrator: {err}", file=sys.stderr)
        sys.exit(1)


def run_seed_data():
    """Execute sample data seeding logic."""
    try:
        db = get_db()
        init_user_indexes(db)
        init_crime_indexes(db)

        admin_user = db.users.find_one({"role": "Admin"})
        admin_id = str(admin_user["_id"]) if admin_user else None

        seeded = seed_sample_crimes(db, creator_id=admin_id)
        print(f"[CRMS] Successfully inserted {len(seeded)} fictional crime records for laboratory testing:")
        for case_no in seeded:
            print(f"       - Case {case_no}")
    except Exception as err:
        print(f"[CRMS ERROR] Could not seed sample data: {err}", file=sys.stderr)
        sys.exit(1)


@app.cli.command("init-admin")
def init_admin_command():
    """Initialize administrator from environment variables."""
    run_init_admin()


@app.cli.command("seed-data")
def seed_data_command():
    """Seed fictional demonstration crime records."""
    run_seed_data()


# ============================================================================
# APPLICATION ENTRYPOINT
# ============================================================================

def setup_database_indexes():
    """Ensure required indexes are registered when starting up."""
    try:
        db = get_db()
        init_user_indexes(db)
        init_crime_indexes(db)
        print("[CRMS] Connected to MongoDB and verified indexes on collections 'users' and 'crimes'.")
    except Exception as e:
        print(f"[CRMS WARNING] Could not verify MongoDB indexes at startup: {e}", file=sys.stderr)


if __name__ == "__main__":
    setup_database_indexes()

    # CLI fallback execution
    if len(sys.argv) > 1 and sys.argv[1] == "init-admin":
        run_init_admin()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "seed-data":
        run_seed_data()
        sys.exit(0)

    print("[CRMS] Starting Crime Record Management System server at http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=True)
