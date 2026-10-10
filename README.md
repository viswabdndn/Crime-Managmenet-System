# Crime Record Management System (CRMS)

**A Complete College Laboratory Project Built Strictly with Python Flask and MongoDB**

---

## 1. Project Title
**Crime Record Management System (CRMS)**  
*Digital Incident Repository, Investigative Dossier Tracking & Civic Crime Intelligence*

---

## 2. Project Abstract
The Crime Record Management System (CRMS) is an academic web application developed to modernize the maintenance of criminal incident logs, investigations, and suspect/victim documentation. Designed specifically as a demonstration of monolithic server-side web engineering, the system operates entirely on Python 3.11+, Flask, and MongoDB (via PyMongo), paired with semantic HTML, custom Vanilla CSS, and server-rendered Jinja2 templates. 

CRMS implements strict role-based access control (Admin, Officer, Viewer), secure session handling, cryptographic password hashing via Werkzeug, session-based Cross-Site Request Forgery (CSRF) defense, and real-time MongoDB aggregation pipelines for intelligence statistics—without requiring any external frontend JavaScript frameworks or separate REST API microservices.

> **Academic Disclaimer:** This is an academic demonstration project. All sample data, case logs, victim statements, suspect descriptions, and officer identifiers are purely fictional. No real personal identifiable information is collected or exposed.

---

## 3. Problem Statement
In traditional and manual law enforcement workflows, incident reports and First Information Reports (FIRs) often suffer from:
1. **Physical Redundancy & Fragmentation:** Paper-based dockets are susceptible to physical damage, loss, and unauthorized alterations.
2. **Search Bottlenecks:** Finding historical records across multiple criteria (date of incident, offense type, case status, location) requires tedious manual ledger audits.
3. **Lack of Centralized Metrics:** Department heads struggle to compute real-time statistics regarding active versus closed investigations or crime rate distribution across jurisdictions.
4. **Weak Role Enforcements:** Physical files lack granular audit trails separating read-only inspection from case modification.

---

## 4. Project Objectives
- Provide a secure, centralized digital repository for incident dossiers.
- Implement server-side authorization separating Administrator, Investigating Officer, and Viewer roles.
- Support comprehensive CRUD (Create, Read, Update, Delete) operations on crime records with unique sequential case tracking (`CRM-YYYY-NNNN`).
- Deliver multi-parameter search and filtration leveraging MongoDB indexes.
- Provide a responsive, real-time dashboard visualizing incident distributions and investigation pipelines through MongoDB aggregation queries without external charting packages.
- Maintain strict architectural purity: zero frontend frameworks (No React/Vue/Angular), zero CSS libraries (No Bootstrap/Tailwind), and a single unified Flask server.

---

## 5. Existing System vs. Proposed System

| Feature | Existing Manual / Fragmented System | Proposed CRMS System |
|---|---|---|
| **Storage Medium** | Physical ledgers or disparate flat files | High-availability MongoDB document collection |
| **Search Mechanism** | Manual page-by-page index searching | Multi-index safe regex and field queries |
| **Case Identification** | Prone to duplicate or illegible numbering | Deterministic, concurrency-safe unique case generator (`CRM-2026-0001`) |
| **Access Control** | Physical lock and key; no granular levels | Role-Based Access Control (`Admin`, `Officer`, `Viewer`) |
| **Statistical Analysis**| Periodic manual tabulations | Instant MongoDB aggregation pipelines |
| **Data Integrity** | Prone to loss or undocumented modifications | Preserved original creation timestamps and server-side validation |

---

## 6. Main Features
1. **Personnel Authentication & Session Management:**
   - Account registration with role defaulting to `Viewer`.
   - Werkzeug secure password hashing (`scrypt`/`pbkdf2`).
   - Session-based CSRF protection on every state-changing form submission.
   - Profile management with optional password updating.
2. **Role-Based Authorization Architecture:**
   - **Admin:** Full rights (Create, Read, Update, Delete crimes; audit and modify user roles; run intelligence analytics).
   - **Officer:** Add new cases, edit assigned/managed dossiers, append investigation notes.
   - **Viewer:** Search, browse, and inspect records and dashboard analytics in read-only mode.
3. **Crime Incident Dossier Management (CRUD):**
   - **Create:** Auto-generated unique case numbers, date parsing, input validation against predefined crime categories and statuses.
   - **Read:** Formatted case file view with printable layout, timestamp audits, and fictional party statements.
   - **Update:** Modify investigative logs, case status, suspect leads while maintaining immutable case numbers.
   - **Delete:** Protected admin-only deletion with confirmation safeguards.
4. **Advanced Multi-Criteria Search & Filter:**
   - General keyword query across title, description, and officer.
   - Offense category filtering.
   - Case status pipeline filtering.
   - Location substring search.
   - Specific case number matching.
   - Date range filter (`from` and `to` on reported dates).
5. **Real-time Analytical Dashboard:**
   - Summary stat cards: Total Cases, Reported, Active Investigations, Closed, Unsolved.
   - Category distribution with percentage bars.
   - Status pipeline breakdown.
   - Recent 5 reported incidents and recent 5 modified investigations.

---

## 7. Technology Stack
- **Backend Language:** Python 3.11+
- **Web Framework:** Flask
- **Database:** MongoDB
- **Database Driver:** PyMongo (with connection pooling)
- **Templating Engine:** Jinja2
- **Password Security:** Werkzeug (`werkzeug.security`)
- **Environment Management:** `python-dotenv`
- **Frontend / Styling:** Pure Semantic HTML5 & Custom Vanilla CSS (`static/css/style.css`)
- **Strictly Excluded:** React, Node.js, npm, Vite, Vue, Angular, Bootstrap, Tailwind CSS, Django, FastAPI, JWT.

---

## 8. System Requirements

### Hardware Requirements
- **Processor:** Dual Core Intel/AMD processor (1.8 GHz or higher)
- **RAM:** Minimum 2 GB (4 GB recommended)
- **Storage:** 500 MB free hard disk space

### Software Requirements
- **Operating System:** Windows 10/11, macOS, or Linux
- **Python:** Version 3.11 or higher (Python 3.14 verified)
- **MongoDB:** Community Server 6.0+ (running locally or MongoDB Atlas)
- **Web Browser:** Any modern web browser (Edge, Chrome, Firefox, Safari)

---

## 9. Project Folder Structure
```
crime-record-management-system/
│
├── app.py                     # Main Flask entrypoint, routes, error handlers, and CLI commands
├── config.py                  # Environment loader, configuration class, and PyMongo client pool
├── requirements.txt           # Minimal exact Python dependencies
├── .env.example               # Example environment variable template
├── .env                       # Local active environment configuration
├── README.md                  # Comprehensive project documentation
│
├── models/
│   ├── __init__.py
│   ├── user_model.py          # User schema, password hashing, role management, and queries
│   └── crime_model.py         # Crime schema, CRUD methods, aggregations, search, and seeding
│
├── templates/
│   ├── base.html              # Core layout template with nav, flash banners, role tags, footer
│   ├── index.html             # Public portal home with system overview and hero actions
│   ├── login.html             # Personnel sign-in form
│   ├── register.html          # New account registration form (default Viewer)
│   ├── dashboard.html         # Crime statistics, metrics, aggregations, and recent logs
│   ├── crimes.html            # Data table of all records with filter/search controls
│   ├── add_crime.html         # New incident registration form
│   ├── edit_crime.html        # Existing incident modification form
│   ├── crime_details.html     # Comprehensive case file dossier view
│   ├── profile.html           # User profile and credentials update
│   ├── admin_users.html       # Administrator panel to view and modify user roles
│   ├── 404.html               # Friendly document not found page
│   └── 500.html               # Friendly internal error page
│
├── static/
│   └── css/
│       └── style.css          # Custom navy & teal civic administration design stylesheet
│
└── utils/
    ├── __init__.py
    └── helpers.py             # Auth decorators, CSRF token helpers, ObjectId parser, case generator
```

---

## 10. MongoDB Setup

### A. Local MongoDB Service (Windows)
1. Ensure MongoDB Community Server is installed on your machine.
2. Verify or start the Windows MongoDB service via PowerShell:
   ```powershell
   Get-Service -Name "MongoDB"
   Start-Service -Name "MongoDB"
   ```
3. Default local connection URI: `mongodb://localhost:27017/`

### B. Remote MongoDB (MongoDB Atlas)
If using MongoDB Atlas cloud cluster:
1. Create a free cluster on [MongoDB Atlas](https://www.mongodb.com/atlas).
2. Create a database user and whitelist your IP address (`0.0.0.0/0` for development).
3. Copy your connection string into your `.env` file:
   ```env
   MONGO_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=crime_record_management
   ```

---

## 11. Virtual Environment Setup & Installation (Windows)

Open PowerShell or Command Prompt in the project root directory:

```powershell
# 1. Create a virtual environment
python -m venv venv

# 2. Activate the virtual environment
venv\Scripts\activate

# 3. Install the exact dependencies
pip install -r requirements.txt
```

---

## 12. Environment Variables (`.env`)
Create a `.env` file in the root directory (based on `.env.example`):

```env
MONGO_URI=mongodb://localhost:27017/
DATABASE_NAME=crime_record_management
SECRET_KEY=crm_secret_key_89f02b1c3e4a5d67891234efac9012cd_2026
ADMIN_EMAIL=admin@crimerecord.local
ADMIN_PASSWORD=AdminPass123!
ADMIN_NAME=Chief Administrator
ADMIN_DEPARTMENT=Headquarters Administration
```

---

## 13. Administrator Initialization
For security, user registration defaults to the `Viewer` role. To initialize the primary administrator without hardcoded database entries, execute:

```powershell
python app.py init-admin
```
*(Or `flask init-admin`)*

This reads `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME`, and `ADMIN_DEPARTMENT` from `.env`, creates the Admin document with Werkzeug password hashing, and establishes MongoDB indexes.

Default Initial Credentials:
- **Email:** `admin@crimerecord.local`
- **Password:** `AdminPass123!`

---

## 14. Optional Fictional Data Seeding
To populate the database with realistic, fictional academic demonstration records for testing:

```powershell
python app.py seed-data
```
*(Or `flask seed-data`)*

This will insert 7 diverse, fictional crime scenarios (Campus Lab Laptop Theft, Spoofed Portal Cybercrime, Amphitheatre Vandalism, Accounts Office Cheque Fraud, Store Burglary, Missing Student, and Roadside Robbery).

---

## 15. Running the Application
Start the Flask web server:

```powershell
python app.py
```

The application is now live at:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 16. Database Collections & Fields

### Collection: `users`
- `_id`: `ObjectId` — Unique user identifier
- `full_name`: `string` — Full personnel name
- `email`: `string` — Unique indexed department email
- `password_hash`: `string` — Werkzeug cryptographic hash
- `department`: `string` — Assigned division or cell
- `role`: `string` — Allowed values: `Admin`, `Officer`, `Viewer` (Default: `Viewer`)
- `created_at`: `datetime` — Account registration timestamp
- `updated_at`: `datetime` — Profile modification timestamp

### Collection: `crimes`
- `_id`: `ObjectId` — Unique document identifier
- `case_number`: `string` — Unique indexed case identifier (e.g. `CRM-2026-0001`)
- `title`: `string` — Short title of incident
- `crime_type`: `string` — Predefined category (Theft, Robbery, Burglary, Assault, Fraud, Cybercrime, Missing Person, Vandalism, Property Crime, Other)
- `description`: `string` — Detailed narrative of the event
- `date_reported`: `datetime` — Indexed timestamp when incident was reported
- `date_of_incident`: `datetime` — Date incident occurred
- `location`: `string` — Indexed incident address or campus landmark
- `victim_details`: `string` — Fictional complainant/victim information
- `suspect_details`: `string` — Suspect identifiers, CCTV descriptions
- `investigating_officer`: `string` — Assigned officer name and badge number
- `investigation_notes`: `string` — Progress notes, forensic updates
- `case_status`: `string` — Indexed pipeline status (Reported, Under Investigation, Evidence Collection, Suspect Identified, Charges Filed, Closed, Unsolved)
- `created_at`: `datetime` — Record creation timestamp
- `updated_at`: `datetime` — Last record modification timestamp
- `created_by`: `string` — User ID of the officer who created the record

### MongoDB Indexes
- `users.email` — Unique index
- `crimes.case_number` — Unique index
- `crimes.crime_type` — Single field index
- `crimes.case_status` — Single field index
- `crimes.date_reported` — Single field index
- `crimes.location` — Single field index

---

## 17. User Roles & Permissions Matrix

| Feature / Action | Admin | Officer | Viewer | Unauthenticated |
|---|:---:|:---:|:---:|:---:|
| Browse Public Home | Yes | Yes | Yes | Yes |
| Sign Up / Register Account | Yes | Yes | Yes | Yes |
| Sign In / Sign Out | Yes | Yes | Yes | Yes |
| View Analytical Dashboard | Yes | Yes | Yes | No (Redirect) |
| Search & Filter Crime Records | Yes | Yes | Yes | No (Redirect) |
| View Detailed Incident Dossier | Yes | Yes | Yes | No (Redirect) |
| Print Case Dossier | Yes | Yes | Yes | No (Redirect) |
| Add New Crime Record | Yes | Yes | **No** | No (Redirect) |
| Edit Existing Crime Record | Yes | Yes | **No** | No (Redirect) |
| Delete Crime Record | **Yes** | **No** | **No** | No (Redirect) |
| Audit Personnel Accounts | **Yes** | **No** | **No** | No (Redirect) |
| Change User Roles | **Yes** | **No** | **No** | No (Redirect) |
| Edit Personal Profile & Password | Yes | Yes | Yes | No (Redirect) |

---

## 18. Application Workflow
```
[User Browser]
       │
       ▼
 [Public Landing Page] ──► [Sign In / Register]
                                    │
                         (Authenticated Session)
                                    ▼
       ┌──────────────────── [Dashboard] ─────────────────────┐
       │                            │                         │
       ▼                            ▼                         ▼
[View All Crimes] ◄────► [Search & Filter] ◄────► [View Case Dossier]
       │                                                      │
(Officer/Admin)                                         (Admin Only)
       │                                                      │
       ▼                                                      ▼
[Add / Edit Crime]                                     [Delete Crime]
       │
       ▼
[MongoDB Document Updates]
```

---

## 19. Testing Instructions

An automated unit and integration test suite is included in the project:

```powershell
python -m unittest tests/test_suite.py
```
*(Or run individual route validation with Python)*

The test suite systematically verifies:
1. Public page rendering (`/`)
2. Authentication flow, sessions, and redirects
3. Default assignment of `Viewer` role on registration
4. Rejection of duplicate email registrations
5. CSRF token validation and blocking of unauthorized POST requests
6. Dashboard statistics and MongoDB aggregation pipelines
7. Multi-criteria search (keyword, type, case number, location)
8. Handling of invalid and non-existent ObjectIds
9. Authorization blocks preventing Viewers from modifying records
10. Full CRUD lifecycle (Add, View, Edit, and Delete)
11. Profile updating and Admin user role modification

---

## 20. Screenshots & UI Layout Walkthrough

1. **Landing Page (`/`):** Dark navy hero section with teal accents, academic laboratory badge, quick CTAs, and system specification summaries.
2. **Dashboard (`/dashboard`):** Real-time statistic cards (Total, Reported, Active, Closed, Unsolved), category distribution bars, case pipeline breakdown, and recent activity tables.
3. **Crime Repository (`/crimes`):** Comprehensive filter toolbar (Search, Case Number, Offense Type, Status, Location, Date Range) with color-coded status badges and role-based action triggers.
4. **Case Dossier (`/crimes/<id>`):** Structured case file presentation with incident narrative, associated fictional persons, evidence logs, metadata timestamps, and print formatting.
5. **Add / Edit Crime (`/crimes/add`, `/crimes/edit/<id>`):** Multi-section forms with server-side validation and immutable case numbers.
6. **User Roles Panel (`/admin/users`):** Administrator table for promoting registered accounts between Viewer, Officer, and Admin.

---

## 21. Limitations
- Designed strictly as a single-server monolithic academic application; does not include distributed message brokers or WebSockets.
- File attachment storage (e.g., actual high-resolution ballistics PDF reports or multi-gigabyte video evidence) is stored textually/metadata-based rather than in cloud object storage (S3/GridFS).
- Email notifications for case status changes are not configured by default to keep external network dependencies zero.

---

## 22. Future Enhancements
- Integration of MongoDB GridFS for binary digital evidence file attachments (audio logs, CCTV clips).
- Automated PDF case dossier generator using Python standard libraries.
- Geographic coordinate mapping using Leaflet and GeoJSON MongoDB spatial queries.
- Biometric authentication integration simulation for high-clearance investigations.
