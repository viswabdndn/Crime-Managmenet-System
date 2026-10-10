import re
import hmac
import secrets
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, flash, request, abort
from bson import ObjectId
from bson.errors import InvalidId


def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator to require specific user roles for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login"))
            
            user_role = session.get("role")
            if user_role not in roles:
                flash("You do not have permission to perform this action.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorator to restrict access strictly to Administrators."""
    return role_required("Admin")(f)


def officer_required(f):
    """Decorator to restrict access to Officers and Administrators."""
    return role_required("Admin", "Officer")(f)


def generate_csrf_token():
    """Generate or retrieve a session-based CSRF token."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf_token(token):
    """Validate submitted CSRF token against session token."""
    session_token = session.get("_csrf_token")
    if not session_token or not token:
        return False
    return hmac.compare_digest(session_token, token)


def parse_object_id(oid_str):
    """
    Safely convert string to BSON ObjectId.
    Returns ObjectId instance or None if invalid.
    """
    if not oid_str or not isinstance(oid_str, str):
        return None
    try:
        return ObjectId(oid_str)
    except (InvalidId, TypeError, ValueError):
        return None


def validate_email(email):
    """Validate email address format."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email.strip()) is not None


def generate_case_number(db):
    """
    Generate a unique case number in the format 'CRM-YYYY-NNNN'.
    E.g., CRM-2026-0001
    """
    current_year = datetime.now().year
    prefix = f"CRM-{current_year}-"
    
    # Find all case numbers for the current year
    regex_pattern = f"^{prefix}\\d{{4}}$"
    existing_records = db.crimes.find(
        {"case_number": {"$regex": regex_pattern}},
        {"case_number": 1}
    ).sort("case_number", -1).limit(1)
    
    max_num = 0
    records_list = list(existing_records)
    if records_list:
        last_case_number = records_list[0].get("case_number", "")
        parts = last_case_number.split("-")
        if len(parts) == 3 and parts[2].isdigit():
            max_num = int(parts[2])
            
    next_num = max_num + 1
    new_case_number = f"{prefix}{next_num:04d}"
    
    # Extra check for uniqueness
    while db.crimes.find_one({"case_number": new_case_number}):
        next_num += 1
        new_case_number = f"{prefix}{next_num:04d}"
        
    return new_case_number


def format_datetime(value, fmt="%b %d, %Y %I:%M %p"):
    """Format datetime object or ISO string for Jinja2 template display."""
    if not value:
        return "N/A"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            return value
    if isinstance(value, datetime):
        return value.strftime(fmt)
    return str(value)


def format_date(value, fmt="%b %d, %Y"):
    """Format date for Jinja2 template display."""
    return format_datetime(value, fmt=fmt)
