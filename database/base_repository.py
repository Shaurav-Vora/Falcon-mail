"""
SENTINEL - Base Repository Interface
Defines the standard repository contract for complaint storage, notifications,
audit trail, and real-time dashboard queries.

Every privileged method strictly takes an `actor: AuthenticatedUser` to enforce
server-side role-based authorization.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from database.auth_context import AuthenticatedUser


class BaseComplaintRepository(ABC):
    """Abstract Base Class for complaint and event persistence."""

    @abstractmethod
    def create_complaint(self, data: Dict[str, Any], actor: AuthenticatedUser) -> str:
        """Insert a newly submitted complaint and return its complaint_id."""
        pass

    @abstractmethod
    def get_complaint_by_id(self, complaint_id: str, actor: AuthenticatedUser) -> Optional[Dict[str, Any]]:
        """Retrieve a complaint by ID.
        Authorization: actor must be admin OR actor.uid must equal complaint.reporter_uid.
        """
        pass

    @abstractmethod
    def get_student_complaints(self, uid: str, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Retrieve all complaints submitted by a given student UID.
        Authorization: actor.uid == uid OR actor.role == 'admin'.
        """
        pass

    @abstractmethod
    def get_all_complaints(self, actor: AuthenticatedUser, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve complaints campus-wide.
        Authorization: actor.role == 'admin'.
        """
        pass

    @abstractmethod
    def get_unresolved_complaints(self, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Retrieve unresolved complaints sorted by Priority (Critical->High->Medium->Low),
        then oldest first.
        Authorization: actor.role == 'admin'.
        """
        pass

    @abstractmethod
    def get_recent_complaints(self, actor: AuthenticatedUser, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent complaints for triage.
        Authorization: actor.role == 'admin'.
        """
        pass

    @abstractmethod
    def get_resolved_cases(self, actor: AuthenticatedUser, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve resolved or rejected complaints archive.
        Authorization: actor.role == 'admin'.
        """
        pass

    @abstractmethod
    def assign_complaint(self, complaint_id: str, actor: AuthenticatedUser) -> Dict[str, Any]:
        """Atomically assign complaint to the current admin.
        Authorization: actor.role == 'admin'.
        Returns dict with success status and message (fails if already claimed by another admin).
        """
        pass

    @abstractmethod
    def update_complaint_status(
        self,
        complaint_id: str,
        new_status: str,
        actor: AuthenticatedUser,
        resolution_note: Optional[str] = None,
    ) -> bool:
        """Update complaint status and append audit event.
        Authorization: actor.role == 'admin'.
        Validation: If new_status is 'Resolved', resolution_note must be non-empty.
                    If new_status is 'Rejected', reason/note must be non-empty.
        """
        pass

    @abstractmethod
    def get_duplicate_candidates(self, actor: AuthenticatedUser, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch candidate complaints for semantic duplicate matching.
        Internal system retrieval only.
        """
        pass

    @abstractmethod
    def create_notification(
        self,
        recipient_uid: str,
        complaint_id: str,
        notif_type: str,
        title: str,
        message: str,
    ) -> str:
        """Create a notification for a user."""
        pass

    @abstractmethod
    def get_student_notifications(self, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Fetch notifications for the authenticated student.
        Authorization: query scoped strictly to recipient_uid == actor.uid.
        """
        pass

    @abstractmethod
    def mark_notification_read(self, notification_id: str, actor: AuthenticatedUser) -> bool:
        """Mark a notification as read.
        Authorization: recipient_uid must match actor.uid or actor is admin.
        """
        pass

    @abstractmethod
    def get_complaint_events(self, complaint_id: str, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Retrieve the immutable audit timeline for a complaint.
        Authorization: actor.is_admin OR actor.uid == complaint.reporter_uid.
        """
        pass

    @abstractmethod
    def get_dashboard_stats(self, actor: AuthenticatedUser) -> Dict[str, Any]:
        """Aggregate statistics.
        Authorization: If actor is admin, returns campus-wide metrics.
        If actor is student, returns strictly personal metrics.
        """
        pass
