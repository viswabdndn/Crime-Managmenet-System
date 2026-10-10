import os
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


if __name__ == "__main__":
    unittest.main()
