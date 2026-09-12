"""
SENTINEL - Authentication & Authorization Context
Defines the AuthenticatedUser dataclass representing an authenticated session actor.
All privileged repository and service functions receive an AuthenticatedUser instance
to enforce server-side authorization and data isolation.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuthenticatedUser:
    """Represents an authenticated student or administrator."""
    uid: str
    email: str
    full_name: str
    role: str  # "student" | "admin"
    student_id: Optional[str] = None
    programme: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_student(self) -> bool:
        return self.role == "student"
