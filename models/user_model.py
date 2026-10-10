from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from utils.helpers import parse_object_id, validate_email

ALLOWED_ROLES = ["Viewer", "Officer", "Admin"]


def init_user_indexes(db):
    """Create indexes for users collection."""
    db.users.create_index("email", unique=True)


def find_by_email(db, email):
    """Find user document by email (case-insensitive)."""
    if not email:
        return None
    return db.users.find_one({"email": email.strip().lower()})


def find_by_id(db, user_id):
    """Find user document by string or ObjectId."""
    oid = parse_object_id(str(user_id))
    if not oid:
        return None
    return db.users.find_one({"_id": oid})


def create_user(db, full_name, email, password, department, role="Viewer"):
    """
    Register a new user in MongoDB.
    Validates email format, checks for duplicates, and hashes password.
    """
    if not full_name or not full_name.strip():
        raise ValueError("Full name is required.")
        
    email_clean = email.strip().lower() if email else ""
    if not validate_email(email_clean):
        raise ValueError("A valid email address is required.")
        
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")
        
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role '{role}'. Allowed roles are: {', '.join(ALLOWED_ROLES)}.")
        
    # Check for duplicate email
    if find_by_email(db, email_clean):
        raise ValueError("An account with this email address already exists.")
        
    now = datetime.now(timezone.utc)
    password_hash = generate_password_hash(password)
    
    user_doc = {
        "full_name": full_name.strip(),
        "email": email_clean,
        "password_hash": password_hash,
        "department": department.strip() if department else "General",
        "role": role,
        "created_at": now,
        "updated_at": now
    }
    
    result = db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    return user_doc


def verify_user_password(stored_hash, password):
    """Verify password against stored Werkzeug hash."""
    if not stored_hash or not password:
        return False
    return check_password_hash(stored_hash, password)


def update_profile(db, user_id, full_name, department, new_password=None):
    """Update user's profile details."""
    oid = parse_object_id(str(user_id))
    if not oid:
        raise ValueError("Invalid user identifier.")
        
    update_fields = {
        "full_name": full_name.strip(),
        "department": department.strip() if department else "General",
        "updated_at": datetime.now(timezone.utc)
    }
    
    if new_password:
        if len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters long.")
        update_fields["password_hash"] = generate_password_hash(new_password)
        
    db.users.update_one({"_id": oid}, {"$set": update_fields})
    return True


def update_role(db, user_id, new_role):
    """Change user role (restricted to Admins)."""
    if new_role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role. Allowed roles are: {', '.join(ALLOWED_ROLES)}")
        
    oid = parse_object_id(str(user_id))
    if not oid:
        raise ValueError("Invalid user identifier.")
        
    target_user = db.users.find_one({"_id": oid})
    if not target_user:
        raise ValueError("User not found.")
        
    # If demoting an admin, ensure they are not the sole admin
    if target_user.get("role") == "Admin" and new_role != "Admin":
        admin_count = count_admins(db)
        if admin_count <= 1:
            raise ValueError("Cannot demote the only remaining Administrator.")
            
    db.users.update_one(
        {"_id": oid},
        {"$set": {"role": new_role, "updated_at": datetime.now(timezone.utc)}}
    )
    return True


def get_all_users(db):
    """Return all users with password hashes omitted, sorted by creation date."""
    users = list(db.users.find({}, {"password_hash": 0}).sort("created_at", -1))
    return users


def count_admins(db):
    """Count how many users currently hold the Admin role."""
    return db.users.count_documents({"role": "Admin"})
