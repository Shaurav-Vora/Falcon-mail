"""
SENTINEL - Server-Side Role-Based Access Control (RBAC) & Data Isolation Tests
Verifies server-side authorization enforcement, data privacy, and resolution validation
using an isolated temporary test repository.
"""

import os
import tempfile
import unittest

from database.auth_context import AuthenticatedUser
from database.sqlite_repository import SQLiteRepository


class TestRBAC(unittest.TestCase):

    def setUp(self):
        # Create an isolated temporary test SQLite database
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.repo = SQLiteRepository(self.temp_db.name)

        # Create two distinct students and an administrator
        self.student_a = AuthenticatedUser(
            uid="student_a_001",
            email="student_a@manipal.edu",
            full_name="Alice Student",
            role="student",
            student_id="210953001",
        )
        self.student_b = AuthenticatedUser(
            uid="student_b_002",
            email="student_b@manipal.edu",
            full_name="Bob Student",
            role="student",
            student_id="210953002",
        )
        self.admin = AuthenticatedUser(
            uid="admin_001",
            email="admin@manipal.edu",
            full_name="Staff Administrator",
            role="admin",
        )

        # Create sample complaints
        self.cid_a = self.repo.create_complaint({
            "title": "Broken AC in Room 101",
            "description": "AC is blowing hot air.",
            "category": "Maintenance",
            "urgency": "Medium",
        }, actor=self.student_a)

        self.cid_b = self.repo.create_complaint({
            "title": "Wi-Fi down in Library",
            "description": "Cannot connect to campus Wi-Fi.",
            "category": "IT",
            "urgency": "High",
        }, actor=self.student_b)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except Exception:
                pass

    def test_student_cannot_access_other_student_complaints(self):
        # Student A retrieving Student B's complaints must raise PermissionError
        with self.assertRaises(PermissionError):
            self.repo.get_student_complaints(self.student_b.uid, actor=self.student_a)

        # Student A viewing Student B's individual complaint by ID must raise PermissionError
        with self.assertRaises(PermissionError):
            self.repo.get_complaint_by_id(self.cid_b, actor=self.student_a)

        # Student A viewing own complaint must succeed
        own_doc = self.repo.get_complaint_by_id(self.cid_a, actor=self.student_a)
        self.assertIsNotNone(own_doc)
        self.assertEqual(own_doc["reporter_uid"], self.student_a.uid)

    def test_student_cannot_execute_admin_methods(self):
        # Student cannot call get_all_complaints
        with self.assertRaises(PermissionError):
            self.repo.get_all_complaints(actor=self.student_a)

        # Student cannot call get_unresolved_complaints
        with self.assertRaises(PermissionError):
            self.repo.get_unresolved_complaints(actor=self.student_a)

        # Student cannot call update_complaint_status
        with self.assertRaises(PermissionError):
            self.repo.update_complaint_status(self.cid_a, "Resolved", actor=self.student_a, resolution_note="Fixed")

        # Student cannot call assign_complaint
        with self.assertRaises(PermissionError):
            self.repo.assign_complaint(self.cid_a, actor=self.student_a)

    def test_admin_can_access_and_triage(self):
        # Admin can view campus-wide complaints
        all_cases = self.repo.get_all_complaints(actor=self.admin)
        self.assertEqual(len(all_cases), 2)

        # Admin can view unresolved queue
        unresolved = self.repo.get_unresolved_complaints(actor=self.admin)
        self.assertEqual(len(unresolved), 2)

    def test_admin_assignment_concurrency(self):
        # Admin 1 claims complaint
        claim_res = self.repo.assign_complaint(self.cid_a, actor=self.admin)
        self.assertTrue(claim_res["success"])

        # Admin 2 attempts to claim already assigned complaint
        admin2 = AuthenticatedUser(
            uid="admin_002",
            email="admin2@manipal.edu",
            full_name="Admin Two",
            role="admin",
        )
        claim_res2 = self.repo.assign_complaint(self.cid_a, actor=admin2)
        self.assertFalse(claim_res2["success"])
        self.assertTrue(claim_res2.get("already_assigned"))

    def test_resolution_note_validation(self):
        # Resolving without note must raise ValueError
        with self.assertRaises(ValueError):
            self.repo.update_complaint_status(self.cid_a, "Resolved", actor=self.admin, resolution_note="")

        with self.assertRaises(ValueError):
            self.repo.update_complaint_status(self.cid_a, "Resolved", actor=self.admin, resolution_note=None)

        # Rejecting without note must raise ValueError
        with self.assertRaises(ValueError):
            self.repo.update_complaint_status(self.cid_a, "Rejected", actor=self.admin, resolution_note="")

        # Resolving with note must succeed
        ok = self.repo.update_complaint_status(
            self.cid_a, "Resolved", actor=self.admin, resolution_note="Maintenance replaced the AC capacitor."
        )
        self.assertTrue(ok)

        # Verify audit event and notification
        events = self.repo.get_complaint_events(self.cid_a, actor=self.admin)
        self.assertTrue(any(e.get("event_type") == "resolved" for e in events))

        notifs = self.repo.get_student_notifications(actor=self.student_a)
        self.assertTrue(any("Resolved" in n.get("title", "") for n in notifs))


if __name__ == "__main__":
    unittest.main()
