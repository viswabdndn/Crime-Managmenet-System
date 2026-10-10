import re
from datetime import datetime, timezone
from utils.helpers import parse_object_id, generate_case_number, generate_sample_evidence_b64

ALLOWED_CRIME_TYPES = [
    "Theft",
    "Robbery",
    "Burglary",
    "Assault",
    "Fraud",
    "Cybercrime",
    "Missing Person",
    "Vandalism",
    "Property Crime",
    "Other"
]

ALLOWED_CASE_STATUSES = [
    "Reported",
    "Under Investigation",
    "Evidence Collection",
    "Suspect Identified",
    "Charges Filed",
    "Closed",
    "Unsolved"
]


def init_crime_indexes(db):
    """Create indexes for crimes collection."""
    db.crimes.create_index("case_number", unique=True)
    db.crimes.create_index("crime_type")
    db.crimes.create_index("case_status")
    db.crimes.create_index("date_reported")
    db.crimes.create_index("location")
    db.crimes.create_index("created_at")
    db.crimes.create_index("updated_at")


def validate_crime_payload(data):
    """Validate submitted crime form fields."""
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("Crime title is required.")
        
    crime_type = (data.get("crime_type") or "").strip()
    if crime_type not in ALLOWED_CRIME_TYPES:
        raise ValueError(f"Invalid crime type. Allowed types: {', '.join(ALLOWED_CRIME_TYPES)}")
        
    case_status = (data.get("case_status") or "Reported").strip()
    if case_status not in ALLOWED_CASE_STATUSES:
        raise ValueError(f"Invalid case status. Allowed statuses: {', '.join(ALLOWED_CASE_STATUSES)}")
        
    location = (data.get("location") or "").strip()
    if not location:
        raise ValueError("Incident location is required.")
        
    date_reported_val = data.get("date_reported")
    if not date_reported_val:
        raise ValueError("Date reported is required.")
        
    date_of_incident_val = data.get("date_of_incident")
    if not date_of_incident_val:
        raise ValueError("Date of incident is required.")
        
    investigating_officer = (data.get("investigating_officer") or "").strip()
    if not investigating_officer:
        raise ValueError("Investigating officer name is required.")


def parse_date_input(val):
    """Safely convert date/datetime input string into datetime object."""
    if not val:
        return datetime.now(timezone.utc)
    if isinstance(val, datetime):
        return val
    try:
        if "T" in val:
            return datetime.fromisoformat(val)
        return datetime.strptime(val, "%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc)


def create_crime(db, form_data, created_by_id, evidence_image=None, evidence_image_data=None, evidence_image_mimetype=None, evidence_image_filename=None):
    """
    Validate, assign unique case number, and insert new crime record.
    Stores evidence photo Base64 directly into MongoDB document.
    """
    validate_crime_payload(form_data)
    
    now = datetime.now(timezone.utc)
    case_number = generate_case_number(db)
    
    date_reported = parse_date_input(form_data.get("date_reported"))
    date_of_incident = parse_date_input(form_data.get("date_of_incident"))
    
    crime_doc = {
        "case_number": case_number,
        "title": form_data.get("title", "").strip(),
        "crime_type": form_data.get("crime_type", "").strip(),
        "description": form_data.get("description", "").strip(),
        "date_reported": date_reported,
        "date_of_incident": date_of_incident,
        "location": form_data.get("location", "").strip(),
        "victim_details": form_data.get("victim_details", "").strip(),
        "suspect_details": form_data.get("suspect_details", "").strip(),
        "investigating_officer": form_data.get("investigating_officer", "").strip(),
        "investigation_notes": form_data.get("investigation_notes", "").strip(),
        "case_status": form_data.get("case_status", "Reported").strip(),
        "evidence_image": evidence_image or None,
        "evidence_image_data": evidence_image_data or None,
        "evidence_image_mimetype": evidence_image_mimetype or None,
        "evidence_image_filename": evidence_image_filename or None,
        "created_by": str(created_by_id) if created_by_id else None,
        "created_at": now,
        "updated_at": now
    }
    
    result = db.crimes.insert_one(crime_doc)
    crime_doc["_id"] = result.inserted_id
    return crime_doc


def get_crime_by_id(db, crime_id):
    """Retrieve single crime record by ObjectId."""
    oid = parse_object_id(str(crime_id))
    if not oid:
        return None
    return db.crimes.find_one({"_id": oid})


def get_crime_by_case_number(db, case_number):
    """Retrieve single crime record by case number."""
    if not case_number:
        return None
    return db.crimes.find_one({"case_number": case_number.strip()})


def update_crime(db, crime_id, form_data, evidence_image=None, evidence_image_data=None, evidence_image_mimetype=None, evidence_image_filename=None, remove_image=False):
    """
    Update an existing crime record.
    Preserves original case number and created_at.
    Handles optional new evidence image upload or removal stored in MongoDB.
    """
    oid = parse_object_id(str(crime_id))
    if not oid:
        raise ValueError("Invalid crime record identifier.")
        
    validate_crime_payload(form_data)
    
    date_reported = parse_date_input(form_data.get("date_reported"))
    date_of_incident = parse_date_input(form_data.get("date_of_incident"))
    
    update_doc = {
        "title": form_data.get("title", "").strip(),
        "crime_type": form_data.get("crime_type", "").strip(),
        "description": form_data.get("description", "").strip(),
        "date_reported": date_reported,
        "date_of_incident": date_of_incident,
        "location": form_data.get("location", "").strip(),
        "victim_details": form_data.get("victim_details", "").strip(),
        "suspect_details": form_data.get("suspect_details", "").strip(),
        "investigating_officer": form_data.get("investigating_officer", "").strip(),
        "investigation_notes": form_data.get("investigation_notes", "").strip(),
        "case_status": form_data.get("case_status", "").strip(),
        "updated_at": datetime.now(timezone.utc)
    }

    if remove_image:
        update_doc["evidence_image"] = None
        update_doc["evidence_image_data"] = None
        update_doc["evidence_image_mimetype"] = None
        update_doc["evidence_image_filename"] = None
    elif evidence_image_data:
        update_doc["evidence_image"] = evidence_image
        update_doc["evidence_image_data"] = evidence_image_data
        update_doc["evidence_image_mimetype"] = evidence_image_mimetype
        update_doc["evidence_image_filename"] = evidence_image_filename
    elif evidence_image:
        update_doc["evidence_image"] = evidence_image
    
    result = db.crimes.update_one({"_id": oid}, {"$set": update_doc})
    if result.matched_count == 0:
        raise ValueError("Crime record not found.")
    return True


def delete_crime(db, crime_id):
    """Delete a crime record by ObjectId (Admin only)."""
    oid = parse_object_id(str(crime_id))
    if not oid:
        raise ValueError("Invalid crime record identifier.")
        
    result = db.crimes.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise ValueError("Crime record not found or already deleted.")
    return True


def search_crimes(db, query=None, crime_type=None, case_status=None, location=None, case_number=None, date_from=None, date_to=None):
    """
    Filter and search crime records using safe MongoDB query construction.
    """
    filter_criteria = {}
    
    # Text query across title, description, investigating officer
    if query and query.strip():
        safe_q = re.escape(query.strip())
        filter_criteria["$or"] = [
            {"title": {"$regex": safe_q, "$options": "i"}},
            {"description": {"$regex": safe_q, "$options": "i"}},
            {"investigating_officer": {"$regex": safe_q, "$options": "i"}},
            {"case_number": {"$regex": safe_q, "$options": "i"}},
            {"location": {"$regex": safe_q, "$options": "i"}}
        ]
        
    # Exact or safe regex filters
    if crime_type and crime_type.strip() and crime_type in ALLOWED_CRIME_TYPES:
        filter_criteria["crime_type"] = crime_type.strip()
        
    if case_status and case_status.strip() and case_status in ALLOWED_CASE_STATUSES:
        filter_criteria["case_status"] = case_status.strip()
        
    if location and location.strip():
        safe_loc = re.escape(location.strip())
        filter_criteria["location"] = {"$regex": safe_loc, "$options": "i"}
        
    if case_number and case_number.strip():
        safe_cn = re.escape(case_number.strip())
        filter_criteria["case_number"] = {"$regex": safe_cn, "$options": "i"}
        
    # Date range filters on date_reported
    date_filter = {}
    if date_from and date_from.strip():
        try:
            d_from = datetime.strptime(date_from.strip(), "%Y-%m-%d")
            date_filter["$gte"] = d_from
        except ValueError:
            pass
            
    if date_to and date_to.strip():
        try:
            d_to = datetime.strptime(date_to.strip(), "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            date_filter["$lte"] = d_to
        except ValueError:
            pass
            
    if date_filter:
        filter_criteria["date_reported"] = date_filter
        
    crimes = list(db.crimes.find(filter_criteria).sort("date_reported", -1))
    return crimes


def get_dashboard_stats(db):
    """
    Aggregate statistics for the dashboard using MongoDB pipelines.
    Returns metrics, breakdowns by type and status, and recent cases.
    """
    total_crimes = db.crimes.count_documents({})
    reported_cases = db.crimes.count_documents({"case_status": "Reported"})
    under_investigation = db.crimes.count_documents({"case_status": "Under Investigation"})
    evidence_collection = db.crimes.count_documents({"case_status": "Evidence Collection"})
    suspect_identified = db.crimes.count_documents({"case_status": "Suspect Identified"})
    charges_filed = db.crimes.count_documents({"case_status": "Charges Filed"})
    closed_cases = db.crimes.count_documents({"case_status": "Closed"})
    unsolved_cases = db.crimes.count_documents({"case_status": "Unsolved"})
    
    # Active investigations combined count
    active_cases = (
        under_investigation + 
        evidence_collection + 
        suspect_identified + 
        charges_filed
    )
    
    # Aggregation by Crime Type
    type_pipeline = [
        {"$group": {"_id": "$crime_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    type_stats = list(db.crimes.aggregate(type_pipeline))
    
    # Aggregation by Case Status
    status_pipeline = [
        {"$group": {"_id": "$case_status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    status_stats = list(db.crimes.aggregate(status_pipeline))
    
    # Recently reported crimes (5 most recent)
    recent_reported = list(db.crimes.find(
        {},
        {"case_number": 1, "title": 1, "crime_type": 1, "date_reported": 1, "case_status": 1, "location": 1}
    ).sort("date_reported", -1).limit(5))
    
    # Recently updated cases (5 most recent)
    recent_updated = list(db.crimes.find(
        {},
        {"case_number": 1, "title": 1, "crime_type": 1, "updated_at": 1, "case_status": 1, "investigating_officer": 1}
    ).sort("updated_at", -1).limit(5))
    
    return {
        "total_crimes": total_crimes,
        "reported_cases": reported_cases,
        "under_investigation": under_investigation,
        "active_cases": active_cases,
        "closed_cases": closed_cases,
        "unsolved_cases": unsolved_cases,
        "type_breakdown": type_stats,
        "status_breakdown": status_stats,
        "recent_reported": recent_reported,
        "recent_updated": recent_updated
    }


def seed_sample_crimes(db, creator_id=None):
    """
    Seed realistic, fictional crime records for college laboratory demonstration.
    """
    sample_records = [
        {
            "title": "Laptop Theft in Computer Science Laboratory",
            "crime_type": "Theft",
            "description": "Two high-performance lab workstations and three laptop computers reported missing from the second-floor CS lab during weekend hours. No signs of forced entry on main doors.",
            "date_reported": "2026-09-15",
            "date_of_incident": "2026-09-14",
            "location": "Academic Block B, Lab 204, Campus East",
            "victim_details": "University Department of Computer Science (Asset Custodian: Prof. R. Sharma)",
            "suspect_details": "Unidentified individual in hooded jacket captured on hallway CCTV footage at 22:15 hrs.",
            "investigating_officer": "Insp. Vikram Rathore (Badge #4092)",
            "investigation_notes": "CCTV logs collected. Access swipe cards audited between 20:00 and 06:00. Two keycards flagged for review.",
            "case_status": "Under Investigation"
        },
        {
            "title": "Phishing and Academic Portal Credential Harvesting",
            "crime_type": "Cybercrime",
            "description": "Mass spoofed emails sent to students and staff requesting password resets via a fraudulent external domain imitating the campus portal.",
            "date_reported": "2026-09-18",
            "date_of_incident": "2026-09-17",
            "location": "Campus Network & IT Infrastructure",
            "victim_details": "Fictional Student Council and 42 campus members who responded to the lure.",
            "suspect_details": "External IP range traced to overseas hosting provider. Domain seized with registrar assistance.",
            "investigating_officer": "Sub-Insp. Priya Nair (Badge #3120, Cyber Cell)",
            "investigation_notes": "Firewall DNS sinkhole implemented. Affected accounts forced password rotation. Server logs preserved for forensic analysis.",
            "case_status": "Evidence Collection"
        },
        {
            "title": "Vandalism and Property Damage at Campus Amphitheatre",
            "crime_type": "Vandalism",
            "description": "Spray paint graffiti and damaged acoustic fixtures discovered on the outdoor amphitheatre stage prior to cultural fest rehearsal.",
            "date_reported": "2026-09-22",
            "date_of_incident": "2026-09-21",
            "location": "Central Quadrangle Open-Air Theatre",
            "victim_details": "Campus Facilities & Student Activities Board",
            "suspect_details": "Group of 3 unidentified youths spotted exiting north gate perimeter fence.",
            "investigating_officer": "Head Constable S. Deshmukh (Badge #1187)",
            "investigation_notes": "Spray paint canisters recovered and sent for latent fingerprint processing. Ground patrol logs cross-verified.",
            "case_status": "Reported"
        },
        {
            "title": "Cheque Forgery and Vendor Payment Fraud",
            "crime_type": "Fraud",
            "description": "Alteration of university bookstore payment voucher and interception of physical bank cheque remitted to textbook supplier.",
            "date_reported": "2026-09-28",
            "date_of_incident": "2026-09-10",
            "location": "Accounts Directorate, Administrative Complex",
            "victim_details": "Fictional Apex Books Distribution Ltd.",
            "suspect_details": "Former temporary clerk with administrative file access.",
            "investigating_officer": "Insp. Vikram Rathore (Badge #4092)",
            "investigation_notes": "Bank signature verification cards compared. Bank account freeze request submitted. Interrogation conducted.",
            "case_status": "Charges Filed"
        },
        {
            "title": "Commercial Burglary at South Gate Convenience Store",
            "crime_type": "Burglary",
            "description": "Padlocks cut on rear loading dock; cash register drawer and high-value packaged inventory stolen overnight.",
            "date_reported": "2026-10-01",
            "date_of_incident": "2026-10-01",
            "location": "Campus South Gate Market, Shop #4",
            "victim_details": "Mr. Anand Verma (Shop Owner, Contact: fictional-av@demo.org)",
            "suspect_details": "Suspect apprehended with stolen merchandise during routine checkpoint patrol.",
            "investigating_officer": "Sub-Insp. Priya Nair (Badge #3120)",
            "investigation_notes": "Stolen property recovered in full. Confession recorded in presence of independent witnesses. Case file closed after charge sheet submission.",
            "case_status": "Closed"
        },
        {
            "title": "Reported Missing Person: Undergraduate Exchange Scholar",
            "crime_type": "Missing Person",
            "description": "Final year student failed to return to international student dormitory after weekend excursion. Mobile phone unreachable.",
            "date_reported": "2026-10-04",
            "date_of_incident": "2026-10-03",
            "location": "Dormitory Tower 4, Room 312",
            "victim_details": "Alex Mercer, Age 21, Visiting Scholar in Environmental Sciences",
            "suspect_details": "No foul play suspected initially; transit tickets inspected.",
            "investigating_officer": "Insp. Anita Roy (Badge #5512)",
            "investigation_notes": "Located safely at national park reserve hostel where mountain cellular network was temporarily offline. Case officially resolved.",
            "case_status": "Closed"
        },
        {
            "title": "Night-time Robbery near Metro Transit Link",
            "crime_type": "Robbery",
            "description": "Victim walking towards transit hub threatened by two assailants on motorcycle demanding wallet and smart watch.",
            "date_reported": "2026-10-07",
            "date_of_incident": "2026-10-06",
            "location": "Station Link Road, West Perimeter Junction",
            "victim_details": "Fictional Resident (K. Mehta, Age 29)",
            "suspect_details": "Two males wearing dark helmets riding black 150cc motorcycle without rear license plate.",
            "investigating_officer": "Sub-Insp. Priya Nair (Badge #3120)",
            "investigation_notes": "Traffic camera footage reviewed along western arterial road. No direct license plate match yet.",
            "case_status": "Unsolved"
        }
    ]
    
    seeded_cases = []
    for record in sample_records:
        dummy_case_no = generate_case_number(db)
        b64_image = generate_sample_evidence_b64(record["title"], dummy_case_no, record["crime_type"])
        created = create_crime(
            db, 
            record, 
            created_by_id=creator_id,
            evidence_image=f"evidence_{record['crime_type'].lower()}_log.svg",
            evidence_image_data=b64_image,
            evidence_image_mimetype="image/svg+xml",
            evidence_image_filename=f"evidence_{record['crime_type'].lower()}_log.svg"
        )
        seeded_cases.append(created["case_number"])
        
    return seeded_cases


def ensure_demo_evidence_photos(db):
    """
    Ensure all existing demonstration crimes have forensic evidence images
    stored directly in the MongoDB database document.
    """
    crimes_without_photo = list(db.crimes.find({
        "$or": [
            {"evidence_image_data": None},
            {"evidence_image_data": {"$exists": False}}
        ]
    }))
    for crime in crimes_without_photo:
        b64_img = generate_sample_evidence_b64(
            crime.get("title", "Forensic Record"), 
            crime.get("case_number", "CRM-RECORD"), 
            crime.get("crime_type", "General")
        )
        db.crimes.update_one(
            {"_id": crime["_id"]},
            {"$set": {
                "evidence_image_data": b64_img,
                "evidence_image_mimetype": "image/svg+xml",
                "evidence_image_filename": f"evidence_{crime.get('case_number', 'record').lower()}_verified.svg"
            }}
        )
