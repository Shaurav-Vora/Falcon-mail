"""
SENTINEL - Authentication & Authorization Unit Tests
Tests student registration validation, session state management, and role resolution.
"""

import unittest
from unittest.mock import patch, MagicMock
from database.auth_context import AuthenticatedUser
from utils.auth import sign_up_student, logout, get_current_user


class TestAuth(unittest.TestCase):

    def test_authenticated_user_dataclass(self):
        student = AuthenticatedUser(
            uid="std123",
            email="student@manipal.edu",
            full_name="Student Test",
            role="student",
            student_id="210953001",
        )
        self.assertTrue(student.is_student)
        self.assertFalse(student.is_admin)

        admin = AuthenticatedUser(
            uid="adm999",
            email="admin@manipal.edu",
            full_name="Admin Test",
            role="admin",
        )
        self.assertTrue(admin.is_admin)
        self.assertFalse(admin.is_student)

    def test_student_registration_validation(self):
        # Missing full name
        ok, user, msg = sign_up_student("", "test@manipal.edu", "123", "B.Tech", "secret123", "secret123")
        self.assertFalse(ok)
        self.assertIn("Full name is required", msg)

        # Invalid email
        ok, user, msg = sign_up_student("John Doe", "invalidemail", "123", "B.Tech", "secret123", "secret123")
        self.assertFalse(ok)
        self.assertIn("valid email", msg)

        # Password mismatch
        ok, user, msg = sign_up_student("John Doe", "test@manipal.edu", "123", "B.Tech", "secret123", "different")
        self.assertFalse(ok)
        self.assertIn("Passwords do not match", msg)

        # Weak password
        ok, user, msg = sign_up_student("John Doe", "test@manipal.edu", "123", "B.Tech", "123", "123")
        self.assertFalse(ok)
        self.assertIn("at least 6 characters", msg)

        # Disallowed email domain
        ok, user, msg = sign_up_student("John Doe", "test@unauthorized.com", "123", "B.Tech", "secret123", "secret123")
        self.assertFalse(ok)
        self.assertIn("restricted to authorized student domains", msg)


if __name__ == "__main__":
    unittest.main()
