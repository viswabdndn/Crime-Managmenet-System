import os
import re
import hmac
import uuid
import base64
import secrets
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, flash, request, abort
from bson import ObjectId
from bson.errors import InvalidId
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def allowed_file(filename):
    """Check if uploaded file has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def process_evidence_image_for_db(file_storage):
    """
    Read uploaded image and convert it to Base64 string for direct MongoDB document storage.
    Returns (base64_string, mimetype, clean_filename) or (None, None, None).
    """
    if not file_storage or not file_storage.filename:
        return None, None, None
    filename = file_storage.filename.strip()
    if not allowed_file(filename):
        raise ValueError("Invalid image format. Allowed extensions: PNG, JPG, JPEG, WEBP, GIF.")
    
    file_bytes = file_storage.read()
    if len(file_bytes) > 16 * 1024 * 1024:
        raise ValueError("Image file size exceeds the 16 MB limit.")
        
    b64_str = base64.b64encode(file_bytes).decode("utf-8")
    mimetype = file_storage.mimetype or "image/jpeg"
    clean_name = secure_filename(filename)
    
    # Reset pointer so downstream callers can still read the file if needed
    file_storage.seek(0)
    return b64_str, mimetype, clean_name


def generate_sample_evidence_b64(case_title, case_number, category):
    """Generate professional forensic evidence banner encoded in Base64 for MongoDB seeding."""
    import html
    safe_title = html.escape(case_title[:55])
    safe_case_no = html.escape(case_number)
    safe_cat = html.escape(category)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 480" width="100%" height="100%">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b1120"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#334155" stroke-width="0.5"/>
    </pattern>
  </defs>
  <rect width="800" height="480" fill="url(#bg)"/>
  <rect width="800" height="480" fill="url(#grid)" opacity="0.6"/>
  <rect x="25" y="25" width="750" height="430" fill="none" stroke="#0ea5e9" stroke-width="2" stroke-dasharray="12,6"/>
  <path d="M 20 50 L 20 20 L 50 20" fill="none" stroke="#38bdf8" stroke-width="4"/>
  <path d="M 780 50 L 780 20 L 750 20" fill="none" stroke="#38bdf8" stroke-width="4"/>
  <path d="M 20 430 L 20 460 L 50 460" fill="none" stroke="#38bdf8" stroke-width="4"/>
  <path d="M 780 430 L 780 460 L 750 460" fill="none" stroke="#38bdf8" stroke-width="4"/>
  <rect x="45" y="45" width="280" height="34" rx="4" fill="#0369a1"/>
  <text x="55" y="68" fill="#ffffff" font-family="monospace, sans-serif" font-size="13" font-weight="bold">POLICE FORENSIC EVIDENCE LOG</text>
  <text x="45" y="130" fill="#94a3b8" font-family="sans-serif" font-size="14" font-weight="bold">CASE IDENTIFIER:</text>
  <text x="45" y="165" fill="#38bdf8" font-family="monospace, sans-serif" font-size="28" font-weight="bold">{safe_case_no}</text>
  <text x="45" y="210" fill="#94a3b8" font-family="sans-serif" font-size="14" font-weight="bold">INCIDENT CLASSIFICATION:</text>
  <text x="45" y="238" fill="#f8fafc" font-family="sans-serif" font-size="20">{safe_cat}</text>
  <text x="45" y="280" fill="#94a3b8" font-family="sans-serif" font-size="14" font-weight="bold">INCIDENT TITLE:</text>
  <text x="45" y="308" fill="#f8fafc" font-family="sans-serif" font-size="16">{safe_title}</text>
  <circle cx="640" cy="240" r="85" fill="none" stroke="#ef4444" stroke-width="3" stroke-dasharray="6,4" opacity="0.85"/>
  <text x="640" y="235" fill="#ef4444" font-family="monospace, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" opacity="0.9">EVIDENCE SECURED</text>
  <text x="640" y="255" fill="#ef4444" font-family="monospace, sans-serif" font-size="11" text-anchor="middle" opacity="0.8">CHAIN OF CUSTODY</text>
  <rect x="45" y="395" width="710" height="40" fill="#0f172a" stroke="#334155" stroke-width="1" rx="4"/>
  <text x="60" y="420" fill="#38bdf8" font-family="monospace, sans-serif" font-size="12">RECORD STORED IN MONGODB &#8226; MIME: image/svg+xml &#8226; VERIFIED DATABASE ASSET</text>
</svg>'''
    return base64.b64encode(svg.encode("utf-8")).decode("utf-8")


def save_evidence_image(file_storage, upload_folder):
    """
    Validate and save uploaded evidence image to disk.
    Returns generated unique filename or raises ValueError.
    """
    if not file_storage or not file_storage.filename:
        return None
    filename = file_storage.filename.strip()
    if not allowed_file(filename):
        raise ValueError("Invalid image format. Allowed extensions: PNG, JPG, JPEG, WEBP, GIF.")
    os.makedirs(upload_folder, exist_ok=True)
    clean_name = secure_filename(filename)
    unique_prefix = uuid.uuid4().hex[:10]
    safe_filename = f"evidence_{unique_prefix}_{clean_name}"
    filepath = os.path.join(upload_folder, safe_filename)
    file_storage.save(filepath)
    return safe_filename


def delete_evidence_image(filename, upload_folder):
    """Safely delete an evidence image file from disk."""
    if not filename:
        return
    try:
        filepath = os.path.join(upload_folder, os.path.basename(filename))
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass


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


def export_crimes_to_csv(crimes):
    """
    Generate RFC 4180 compliant CSV string containing crime records.
    """
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    
    # Standard CSV Header
    writer.writerow([
        "Case Number",
        "Title",
        "Crime Type",
        "Case Status",
        "Location",
        "Date of Incident",
        "Date Reported",
        "Investigating Officer",
        "Victim Details",
        "Suspect Details",
        "Investigation Notes",
        "Created At",
        "Updated At"
    ])
    
    for c in crimes:
        writer.writerow([
            c.get("case_number", ""),
            c.get("title", ""),
            c.get("crime_type", ""),
            c.get("case_status", ""),
            c.get("location", ""),
            format_date(c.get("date_of_incident")),
            format_date(c.get("date_reported")),
            c.get("investigating_officer", ""),
            c.get("victim_details", ""),
            c.get("suspect_details", ""),
            c.get("investigation_notes", ""),
            format_datetime(c.get("created_at")),
            format_datetime(c.get("updated_at"))
        ])
        
    return output.getvalue()


def _pdf_escape(text):
    """Sanitize strings for PDF 1.4 literal string inclusion."""
    if not text:
        return ""
    safe = str(text).encode("latin1", errors="replace").decode("latin1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def generate_dossier_pdf(crime):
    """
    Generate an official, professional Police Incident Dossier (FIR Document)
    in standard PDF 1.4 format using pure Python standard library.
    """
    import textwrap
    stream_cmds = []
    
    # 1. Header Banner (#0f172a navy)
    stream_cmds.append("0.06 0.09 0.16 rg")
    stream_cmds.append("36 716 540 44 re f")
    
    # Header Title
    stream_cmds.append("BT")
    stream_cmds.append("/F1 15 Tf")
    stream_cmds.append("1 1 1 rg")
    stream_cmds.append("48 732 Td")
    stream_cmds.append("(CRIME RECORD MANAGEMENT SYSTEM | POLICE DOSSIER) Tj")
    stream_cmds.append("ET")
    
    # Subheader Bar (#0284c7 cyan/teal)
    stream_cmds.append("0.01 0.52 0.78 rg")
    stream_cmds.append("36 698 540 18 re f")
    
    stream_cmds.append("BT")
    stream_cmds.append("/F1 9 Tf")
    stream_cmds.append("1 1 1 rg")
    stream_cmds.append("48 703 Td")
    case_no = _pdf_escape(crime.get("case_number", "CRM-RECORD"))
    status = _pdf_escape(crime.get("case_status", "Reported"))
    category = _pdf_escape(crime.get("crime_type", "General"))
    stream_cmds.append(f"(CASE IDENTIFIER: {case_no}   |   STATUS: {status}   |   CATEGORY: {category}) Tj")
    stream_cmds.append("ET")
    
    # Outer page border
    stream_cmds.append("0.8 0.85 0.9 RG")
    stream_cmds.append("0.75 w")
    stream_cmds.append("36 36 540 724 re S")
    
    # Metadata Grid Box
    stream_cmds.append("0.96 0.97 0.98 rg")
    stream_cmds.append("46 590 520 96 re f")
    stream_cmds.append("0.85 0.88 0.92 RG")
    stream_cmds.append("46 590 520 96 re S")
    
    meta_rows = [
        ("Incident Title:", crime.get("title", "Untitled Case")),
        ("Location:", crime.get("location", "Not specified")),
        ("Date of Incident:", format_date(crime.get("date_of_incident"))),
        ("Date Reported:", format_date(crime.get("date_reported"))),
        ("Investigating Officer:", crime.get("investigating_officer", "Unassigned"))
    ]
    
    curr_y = 668
    for label, val in meta_rows:
        stream_cmds.append("BT")
        stream_cmds.append("/F1 9 Tf")
        stream_cmds.append("0.3 0.35 0.42 rg")
        stream_cmds.append(f"56 {curr_y} Td")
        stream_cmds.append(f"({_pdf_escape(label)}) Tj")
        stream_cmds.append("0.06 0.09 0.16 rg")
        stream_cmds.append("120 0 Td")
        stream_cmds.append(f"({_pdf_escape(val)[:65]}) Tj")
        stream_cmds.append("ET")
        curr_y -= 16
        
    # Content Sections
    sections = [
        ("INCIDENT NARRATIVE & DETAILS", crime.get("description", "No narrative filed.")),
        ("COMPLAINANT / VICTIM INFORMATION", crime.get("victim_details", "None recorded.")),
        ("SUSPECT IDENTIFIERS & CCTV DESCRIPTIONS", crime.get("suspect_details", "No suspects identified.")),
        ("INVESTIGATION PROGRESS & EVIDENCE LOG", crime.get("investigation_notes", "No investigative progress notes filed."))
    ]
    
    sec_y = 560
    for sec_title, sec_content in sections:
        # Section Header bar
        stream_cmds.append("0.92 0.95 0.98 rg")
        stream_cmds.append(f"46 {sec_y - 4} 520 16 re f")
        
        stream_cmds.append("BT")
        stream_cmds.append("/F1 8.5 Tf")
        stream_cmds.append("0.02 0.4 0.65 rg")
        stream_cmds.append(f"52 {sec_y} Td")
        stream_cmds.append(f"({_pdf_escape(sec_title)}) Tj")
        stream_cmds.append("ET")
        
        sec_y -= 18
        
        lines = textwrap.wrap(str(sec_content or "N/A"), width=95)
        if not lines:
            lines = ["N/A"]
            
        for line in lines[:5]:
            stream_cmds.append("BT")
            stream_cmds.append("/F1 8 Tf")
            stream_cmds.append("0.12 0.15 0.2 rg")
            stream_cmds.append(f"54 {sec_y} Td")
            stream_cmds.append(f"({_pdf_escape(line)}) Tj")
            stream_cmds.append("ET")
            sec_y -= 12
            
        sec_y -= 8
        if sec_y < 120:
            break
            
    # Footer Divider
    stream_cmds.append("0.85 0.88 0.92 RG")
    stream_cmds.append("0.5 w")
    stream_cmds.append("46 80 520 0.5 re S")
    
    # Official Seal Stamp box
    stream_cmds.append("0.95 0.97 1.0 rg")
    stream_cmds.append("380 44 186 28 re f")
    stream_cmds.append("0.02 0.4 0.65 RG")
    stream_cmds.append("380 44 186 28 re S")
    
    stream_cmds.append("BT")
    stream_cmds.append("/F1 7.5 Tf")
    stream_cmds.append("0.02 0.4 0.65 rg")
    stream_cmds.append("388 58 Td")
    stream_cmds.append("(CRMS OFFICIAL RECORD - VERIFIED DIGITAL DOSSIER) Tj")
    stream_cmds.append("0 -10 Td")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    stream_cmds.append(f"(Generated: {now_str}) Tj")
    stream_cmds.append("ET")
    
    # Left footer notes
    stream_cmds.append("BT")
    stream_cmds.append("/F1 7.5 Tf")
    stream_cmds.append("0.4 0.45 0.5 rg")
    stream_cmds.append("48 62 Td")
    stream_cmds.append("(Official computer-generated incident docket from Crime Record Management System.) Tj")
    stream_cmds.append("0 -10 Td")
    stream_cmds.append("(Digital evidence, timestamps, and audit trail preserved in MongoDB database.) Tj")
    stream_cmds.append("ET")
    
    content_str = "\n".join(stream_cmds)
    content_bytes = content_str.encode("latin1")
    
    objs = []
    objs.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objs.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objs.append("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
    objs.append(f"4 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n{content_str}\nendstream\nendobj\n")
    objs.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    
    header = "%PDF-1.4\n"
    body = ""
    xref = ["xref\n0 6\n0000000000 65535 f \n"]
    offset = len(header)
    for obj in objs:
        xref.append(f"{offset:010d} 00000 n \n")
        body += obj
        offset += len(obj.encode("latin1"))
        
    xref_str = "".join(xref)
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{offset}\n%%EOF\n"
    return (header + body + xref_str + trailer).encode("latin1")

