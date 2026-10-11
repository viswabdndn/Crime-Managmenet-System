import os
import io
import sys
import re
import unittest
from bson import ObjectId

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db
from models.user_model import find_by_email
from models.crime_model import search_crimes, get_dashboard_stats


class CRMSComprehensiveTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.db = get_db()

    def get_csrf_token(self, response_data):
        """Extract CSRF token from rendered HTML."""
        match = re.search(r'name="csrf_token"\s+value="([a-f0-9]+)"', response_data.decode("utf-8"))
        if match:
            return match.group(1)
        return None

    def test_01_index_page(self):
        """Verify landing page renders successfully."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Crime Record Management", res.data)

    def test_02_login_and_session(self):
        """Verify login sets session and redirects to dashboard."""
        res = self.client.get("/login")
        token = self.get_csrf_token(res.data)
        self.assertIsNotNone(token)

        login_res = self.client.post("/login", data={
            "csrf_token": token,
            "email": "admin@crimerecord.local",
            "password": "AdminPass123!"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b"Chief Administrator", login_res.data)
        self.assertIn(b"Dashboard", login_res.data)

    def test_03_registration_viewer_role(self):
        """Verify new registration defaults to Viewer role."""
        res = self.client.get("/register")
        token = self.get_csrf_token(res.data)
        self.assertIsNotNone(token)

        test_email = "testviewer@college.edu"
        self.db.users.delete_one({"email": test_email})

        reg_res = self.client.post("/register", data={
            "csrf_token": token,
            "full_name": "Test Viewer Officer",
            "email": test_email,
            "department": "Campus Security",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        
        user = find_by_email(self.db, test_email)
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "Viewer")
        self.assertNotEqual(user["password_hash"], "Password123!")

    def test_04_duplicate_registration_prevented(self):
        """Verify duplicate email registration is rejected."""
        res = self.client.get("/register")
        token = self.get_csrf_token(res.data)
        self.assertIsNotNone(token)

        reg_res = self.client.post("/register", data={
            "csrf_token": token,
            "full_name": "Another User",
            "email": "admin@crimerecord.local",
            "department": "Admin",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertIn(b"already exists", reg_res.data)

    def test_05_csrf_protection_rejection(self):
        """Verify POST without CSRF token is rejected."""
        res = self.client.post("/login", data={
            "email": "admin@crimerecord.local",
            "password": "AdminPass123!"
        }, follow_redirects=True)
        self.assertIn(b"Security check failed", res.data)

    def test_06_dashboard_aggregations(self):
        """Verify dashboard statistics and MongoDB aggregation pipelines."""
        stats = get_dashboard_stats(self.db)
        self.assertGreaterEqual(stats["total_crimes"], 7)
        self.assertIn("type_breakdown", stats)
        self.assertIn("status_breakdown", stats)
        self.assertIn("recent_reported", stats)
        self.assertIn("recent_updated", stats)

    def test_07_crime_search_and_filter(self):
        """Verify MongoDB search and filtering."""
        theft_results = search_crimes(self.db, crime_type="Theft")
        for c in theft_results:
            self.assertEqual(c["crime_type"], "Theft")

        q_results = search_crimes(self.db, query="Laptop")
        self.assertTrue(len(q_results) >= 1)
        self.assertIn("Laptop", q_results[0]["title"])

        cn_results = search_crimes(self.db, case_number="CRM-2026-0001")
        self.assertEqual(len(cn_results), 1)
        self.assertEqual(cn_results[0]["case_number"], "CRM-2026-0001")

    def test_08_invalid_object_id_handling(self):
        """Verify invalid ObjectId does not cause server error."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = str(ObjectId())
            sess["role"] = "Viewer"
            sess["user_name"] = "Viewer Test"

        res = self.client.get("/crimes/invalid-id-string-123", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"does not exist or has an invalid identifier", res.data)

    def test_09_viewer_cannot_add_or_delete(self):
        """Verify Viewer role cannot access add crime or delete crime."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = str(ObjectId())
            sess["role"] = "Viewer"
            sess["user_name"] = "Viewer Test"

        res = self.client.get("/crimes/add", follow_redirects=True)
        self.assertIn(b"You do not have permission to perform this action", res.data)

    def test_10_crud_crime_cycle(self):
        """Verify full Create, Read, Update, Delete cycle for crimes."""
        admin = find_by_email(self.db, "admin@crimerecord.local")
        with self.client.session_transaction() as sess:
            sess["user_id"] = str(admin["_id"])
            sess["role"] = "Admin"
            sess["user_name"] = "Chief Administrator"

        # 1. Create crime
        res_add = self.client.get("/crimes/add")
        token = self.get_csrf_token(res_add.data)
        self.assertIsNotNone(token)
        
        post_res = self.client.post("/crimes/add", data={
            "csrf_token": token,
            "title": "Automated Unit Test Incident",
            "crime_type": "Cybercrime",
            "location": "Server Room 101",
            "date_of_incident": "2026-10-09",
            "date_reported": "2026-10-09",
            "description": "Created during automated integration test run.",
            "investigating_officer": "Insp. Automated Test",
            "case_status": "Reported",
            "victim_details": "Test Complainant",
            "suspect_details": "Test Suspect",
            "investigation_notes": "Initial logging."
        }, follow_redirects=True)
        self.assertEqual(post_res.status_code, 200)
        self.assertIn(b"Automated Unit Test Incident", post_res.data)

        # Find created record
        created = self.db.crimes.find_one({"title": "Automated Unit Test Incident"})
        self.assertIsNotNone(created)
        crime_id = str(created["_id"])

        # 2. Read details
        res_det = self.client.get(f"/crimes/{crime_id}")
        self.assertEqual(res_det.status_code, 200)
        self.assertIn(created["case_number"].encode("utf-8"), res_det.data)

        # 3. Update crime
        res_edit = self.client.get(f"/crimes/edit/{crime_id}")
        edit_token = self.get_csrf_token(res_edit.data)
        self.assertIsNotNone(edit_token)
        
        upd_res = self.client.post(f"/crimes/edit/{crime_id}", data={
            "csrf_token": edit_token,
            "title": "Automated Unit Test Incident (Updated)",
            "crime_type": "Cybercrime",
            "location": "Server Room 101",
            "date_of_incident": "2026-10-09",
            "date_reported": "2026-10-09",
            "description": "Updated description.",
            "investigating_officer": "Insp. Automated Test",
            "case_status": "Under Investigation",
            "victim_details": "Test Complainant",
            "suspect_details": "Test Suspect Identified",
            "investigation_notes": "Progress note added."
        }, follow_redirects=True)
        self.assertEqual(upd_res.status_code, 200)
        self.assertIn(b"Updated", upd_res.data)

        # 4. Delete crime (Admin only)
        res_det2 = self.client.get(f"/crimes/{crime_id}")
        del_token = self.get_csrf_token(res_det2.data)
        self.assertIsNotNone(del_token)
        
        del_res = self.client.post(f"/crimes/delete/{crime_id}", data={
            "csrf_token": del_token
        }, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertIn(b"deleted successfully", del_res.data)

        # Verify document is removed from database
        self.assertIsNone(self.db.crimes.find_one({"_id": ObjectId(crime_id)}))

    def test_11_user_profile_and_admin_role_update(self):
        """Verify user profile editing and admin updating user roles."""
        admin = find_by_email(self.db, "admin@crimerecord.local")
        with self.client.session_transaction() as sess:
            sess["user_id"] = str(admin["_id"])
            sess["role"] = "Admin"
            sess["user_name"] = "Chief Administrator"

        # Profile view
        res_prof = self.client.get("/profile")
        self.assertEqual(res_prof.status_code, 200)
        self.assertIn(b"Personnel Profile", res_prof.data)

        # Admin users panel
        res_users = self.client.get("/admin/users")
        self.assertEqual(res_users.status_code, 200)
        self.assertIn(b"Personnel Access", res_users.data)

    def test_12_evidence_image_upload_and_lifecycle(self):
        """Verify uploading crime scene photo, dossier rendering, replacement, and deletion."""
        admin = find_by_email(self.db, "admin@crimerecord.local")
        with self.client.session_transaction() as sess:
            sess["user_id"] = str(admin["_id"])
            sess["role"] = "Admin"
            sess["user_name"] = "Chief Administrator"

        # 1. Fetch CSRF token for add form
        res_add = self.client.get("/crimes/add")
        token = self.get_csrf_token(res_add.data)
        self.assertIsNotNone(token)

        # 2. Upload new crime with evidence image
        mock_image = (io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_evidence_bytes"), "crime_scene.png")
        post_res = self.client.post("/crimes/add", data={
            "csrf_token": token,
            "title": "Incident with Photographic Evidence",
            "crime_type": "Robbery",
            "location": "North Campus Gate (GPS: 28.7041, 77.1025)",
            "date_of_incident": "2026-10-10",
            "date_reported": "2026-10-10",
            "description": "Suspect left physical footprint at northern boundary.",
            "investigating_officer": "Insp. Photographic Test",
            "case_status": "Evidence Collection",
            "victim_details": "Campus Security Guard",
            "suspect_details": "Unknown masked individual",
            "investigation_notes": "Forensic team captured digital photographs.",
            "evidence_image": mock_image
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(post_res.status_code, 200)

        # Verify in database document directly
        crime_doc = self.db.crimes.find_one({"title": "Incident with Photographic Evidence"})
        self.assertIsNotNone(crime_doc)
        self.assertIsNotNone(crime_doc.get("evidence_image"))
        self.assertIsNotNone(crime_doc.get("evidence_image_data"))
        self.assertEqual(crime_doc.get("evidence_image_filename"), "crime_scene.png")
        evidence_file = crime_doc["evidence_image"]

        # Verify streaming directly from MongoDB database route
        crime_id = str(crime_doc["_id"])
        res_photo = self.client.get(f"/crimes/{crime_id}/photo")
        self.assertEqual(res_photo.status_code, 200)
        self.assertEqual(res_photo.data, b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_evidence_bytes")

        # Verify file exists on disk as backup
        saved_path = os.path.join(app.config["UPLOAD_FOLDER"], evidence_file)
        self.assertTrue(os.path.exists(saved_path))

        # 3. Verify details dossier renders photo section, view map button, and database badge
        res_det = self.client.get(f"/crimes/{crime_id}")
        self.assertEqual(res_det.status_code, 200)
        self.assertIn(b"Crime Scene Photographic Evidence", res_det.data)
        self.assertIn(b"FETCHED FROM MONGODB DATABASE", res_det.data)
        self.assertIn(b"View Map", res_det.data)

        # 4. Remove image via edit form
        res_edit = self.client.get(f"/crimes/edit/{crime_id}")
        edit_token = self.get_csrf_token(res_edit.data)
        self.assertIsNotNone(edit_token)

        edit_res = self.client.post(f"/crimes/edit/{crime_id}", data={
            "csrf_token": edit_token,
            "title": "Incident with Photographic Evidence",
            "crime_type": "Robbery",
            "location": "North Campus Gate (GPS: 28.7041, 77.1025)",
            "date_of_incident": "2026-10-10",
            "date_reported": "2026-10-10",
            "description": "Suspect left physical footprint at northern boundary.",
            "investigating_officer": "Insp. Photographic Test",
            "case_status": "Suspect Identified",
            "victim_details": "Campus Security Guard",
            "suspect_details": "Unknown masked individual",
            "investigation_notes": "Forensic team captured digital photographs.",
            "remove_evidence_image": "1"
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)

        updated_doc = self.db.crimes.find_one({"_id": ObjectId(crime_id)})
        self.assertIsNone(updated_doc.get("evidence_image"))
        self.assertIsNone(updated_doc.get("evidence_image_data"))
        # Old file should have been deleted from disk
        self.assertFalse(os.path.exists(saved_path))
        # Photo route now returns 404
        self.assertEqual(self.client.get(f"/crimes/{crime_id}/photo").status_code, 404)

        # 5. Clean up by deleting the crime record
        res_det2 = self.client.get(f"/crimes/{crime_id}")
        del_token = self.get_csrf_token(res_det2.data)
        del_res = self.client.post(f"/crimes/delete/{crime_id}", data={"csrf_token": del_token}, follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertIsNone(self.db.crimes.find_one({"_id": ObjectId(crime_id)}))

    def test_12_export_crimes_csv(self):
        """Verify RFC 4180 CSV export of filtered crime records."""
        # Log in first
        res = self.client.get("/login")
        token = self.get_csrf_token(res.data)
        self.client.post("/login", data={
            "csrf_token": token,
            "email": "admin@crimerecord.local",
            "password": "AdminPass123!"
        }, follow_redirects=True)

        # Request CSV export
        export_res = self.client.get("/crimes/export/csv")
        self.assertEqual(export_res.status_code, 200)
        self.assertIn("text/csv", export_res.content_type)
        self.assertIn("CRMS_Crime_Export_", export_res.headers.get("Content-Disposition", ""))
        self.assertIn(b"Case Number,Title,Crime Type", export_res.data)

    def test_13_export_crime_dossier_pdf(self):
        """Verify standard PDF 1.4 police incident dossier export."""
        # Log in first
        res = self.client.get("/login")
        token = self.get_csrf_token(res.data)
        self.client.post("/login", data={
            "csrf_token": token,
            "email": "admin@crimerecord.local",
            "password": "AdminPass123!"
        }, follow_redirects=True)

        crime = self.db.crimes.find_one()
        self.assertIsNotNone(crime)
        crime_id = str(crime["_id"])

        pdf_res = self.client.get(f"/crimes/{crime_id}/pdf")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.content_type, "application/pdf")
        self.assertIn("Police_Dossier_", pdf_res.headers.get("Content-Disposition", ""))
        self.assertTrue(pdf_res.data.startswith(b"%PDF-1.4"))
        self.assertIn(b"%%EOF", pdf_res.data)


if __name__ == "__main__":
    unittest.main()
