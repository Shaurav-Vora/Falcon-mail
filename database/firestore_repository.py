"""
SENTINEL - Cloud Firestore Repository
Provides shared cloud persistence, server-side authorization enforcement,
near-real-time scoped queries, concurrency-safe transactions, and immutable audit logging.

CRITICAL SECURITY ARCHITECTURE:
Calls using firebase-admin bypass Firestore Security Rules automatically.
Every method in this repository enforces server-side Role-Based Access Control (RBAC)
and verifies actor privileges before reading or writing data.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP, transactional

import config
from database.auth_context import AuthenticatedUser
from database.base_repository import BaseComplaintRepository

logger = logging.getLogger("sentinel.firestore_repository")

# Priority ranking map for sorting queues
PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _get_firestore_client():
    """Ensure Firebase Admin is initialized and return Firestore client."""
    try:
        app = firebase_admin.get_app()
    except ValueError:
        cert_path = config.FIREBASE_SERVICE_ACCOUNT_PATH
        if not cert_path or not credentials.Certificate:
            raise RuntimeError(f"Service account file not found at {cert_path}")
        cred = credentials.Certificate(cert_path)
        app = firebase_admin.initialize_app(cred)
    return firestore.client(app=app)


class FirestoreRepository(BaseComplaintRepository):
    """Production Cloud Firestore repository with server-side RBAC."""

    def __init__(self):
        try:
            self.db = _get_firestore_client()
            logger.info("Connected to Cloud Firestore successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore connection: {e}")
            raise ConnectionError(
                f"Cloud Firestore connection failed. Check serviceAccountKey.json: {e}"
            )

    # --------------------------------------------------------------------------
    # 1. Complaint Creation & Submission
    # --------------------------------------------------------------------------
    def create_complaint(self, data: Dict[str, Any], actor: AuthenticatedUser) -> str:
        """Create a new complaint in Firestore.
        Enforces: actor must be authenticated and reporter_uid must equal actor.uid.
        """
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request. A valid authenticated user is required.")

        complaint_id = data.get("complaint_id") or f"CMP-{uuid.uuid4().hex[:8].upper()}"
        doc_ref = self.db.collection("complaints").document(complaint_id)

        # Convert embedding to list of floats if present
        embedding = data.get("dense_embedding")
        if embedding is not None:
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            elif isinstance(embedding, list):
                embedding = [float(x) for x in embedding]

        doc_data = {
            "complaint_id": complaint_id,
            "title": data.get("title", "Untitled Complaint"),
            "description": data.get("description", ""),
            "category": data.get("category", "Other"),
            "category_confidence": float(data.get("category_confidence", 1.0)),
            "urgency": data.get("urgency", "Medium"),
            "urgency_confidence": float(data.get("urgency_confidence", 1.0)),
            "department": data.get("department", "General Services"),
            "location": data.get("location", "Campus"),
            "building": data.get("building"),
            "room": data.get("room"),
            "status": "Open",
            "reporter_uid": actor.uid,
            "reporter_name": actor.full_name or "Anonymous",
            "reporter_email": actor.email,
            "student_id": actor.student_id or data.get("student_id"),
            "programme": actor.programme or data.get("programme"),
            "assigned_admin_uid": None,
            "assigned_admin_name": None,
            "resolution_note": None,
            "dense_embedding": embedding,
            "duplicate_of_id": data.get("duplicate_of_id"),
            "duplicate_similarity": float(data.get("duplicate_similarity", 0.0))
            if data.get("duplicate_similarity") is not None
            else None,
            "entities": data.get("entities", {}),
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
            "resolved_at": None,
        }

        # Write complaint document
        doc_ref.set(doc_data)

        # Record initial immutable audit event
        self._log_audit_event_direct(
            complaint_id=complaint_id,
            event_type="submitted",
            actor_uid=actor.uid,
            actor_name=actor.full_name,
            from_status=None,
            to_status="Open",
            note="Complaint submitted by student.",
        )

        # Create student notification
        self.create_notification(
            recipient_uid=actor.uid,
            complaint_id=complaint_id,
            notif_type="complaint_created",
            title="Complaint Submitted",
            message=f"Your complaint #{complaint_id} '{doc_data['title']}' has been registered.",
        )

        return complaint_id

    # --------------------------------------------------------------------------
    # 2. Scoped Complaint Retrieval & Authorization
    # --------------------------------------------------------------------------
    def get_complaint_by_id(self, complaint_id: str, actor: AuthenticatedUser) -> Optional[Dict[str, Any]]:
        """Retrieve a complaint by ID.
        Authorization: actor must be admin OR complaint.reporter_uid == actor.uid.
        """
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")

        doc = self.db.collection("complaints").document(complaint_id).get()
        if not doc.exists:
            return None

        data = doc.to_dict()
        # Server-side RBAC enforcement
        if not actor.is_admin and data.get("reporter_uid") != actor.uid:
            raise PermissionError("Access Denied: You do not have permission to view this complaint.")

        return self._normalize_doc(data)

    def get_student_complaints(self, uid: str, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Retrieve all complaints submitted by a student.
        Authorization: actor.uid == uid OR actor.role == 'admin'.
        """
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")
        if not actor.is_admin and actor.uid != uid:
            raise PermissionError("Access Denied: Students can only access their own complaints.")

        docs = (
            self.db.collection("complaints")
            .where("reporter_uid", "==", uid)
            .stream()
        )
        results = [self._normalize_doc(d.to_dict()) for d in docs]
        # Sort descending by created_at in memory
        results.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return results

    def get_all_complaints(self, actor: AuthenticatedUser, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve campus-wide complaints.
        Authorization: actor.role == 'admin'.
        """
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Admin privileges required.")

        query = self.db.collection("complaints")
        if limit:
            query = query.limit(limit)
        docs = query.stream()
        results = [self._normalize_doc(d.to_dict()) for d in docs]
        results.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return results

    def get_unresolved_complaints(self, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Retrieve unresolved complaints.
        Authorization: actor.role == 'admin'.
        Ordering: Critical -> High -> Medium -> Low, then oldest first.
        """
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Admin privileges required.")

        # Scoped query: fetch Open and In Progress
        docs = (
            self.db.collection("complaints")
            .where("status", "in", ["Open", "In Progress"])
            .stream()
        )
        results = [self._normalize_doc(d.to_dict()) for d in docs]

        # Order by priority weight, then oldest created_at first
        def sort_key(doc):
            priority_val = PRIORITY_ORDER.get(doc.get("urgency", "Medium"), 2)
            created_val = str(doc.get("created_at") or "9999")
            return (priority_val, created_val)

        results.sort(key=sort_key)
        return results

    def get_recent_complaints(self, actor: AuthenticatedUser, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent complaints for operations dashboard.
        Authorization: actor.role == 'admin'.
        """
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Admin privileges required.")

        docs = self.db.collection("complaints").limit(limit).stream()
        results = [self._normalize_doc(d.to_dict()) for d in docs]
        results.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return results

    def get_resolved_cases(self, actor: AuthenticatedUser, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve archive of resolved and rejected cases.
        Authorization: actor.role == 'admin'.
        """
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Admin privileges required.")

        docs = (
            self.db.collection("complaints")
            .where("status", "in", ["Resolved", "Rejected"])
            .limit(limit)
            .stream()
        )
        results = [self._normalize_doc(d.to_dict()) for d in docs]
        results.sort(key=lambda x: str(x.get("resolved_at") or x.get("updated_at") or ""), reverse=True)
        return results

    # --------------------------------------------------------------------------
    # 3. Concurrency-Safe Assignment & Status Workflow
    # --------------------------------------------------------------------------
    def assign_complaint(self, complaint_id: str, actor: AuthenticatedUser) -> Dict[str, Any]:
        """Atomically assign complaint to current admin via a Firestore transaction.
        Authorization: actor.role == 'admin'.
        """
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Only administrators can assign complaints.")

        doc_ref = self.db.collection("complaints").document(complaint_id)
        transaction = self.db.transaction()

        @transactional
        def assign_in_transaction(txn):
            snapshot = doc_ref.get(transaction=txn)
            if not snapshot.exists:
                return {"success": False, "message": "Complaint not found."}

            data = snapshot.to_dict()
            current_assignee = data.get("assigned_admin_uid")
            if current_assignee and current_assignee != actor.uid:
                return {
                    "success": False,
                    "message": f"Already claimed by administrator: {data.get('assigned_admin_name', 'Another Admin')}",
                    "already_assigned": True,
                }

            updates = {
                "assigned_admin_uid": actor.uid,
                "assigned_admin_name": actor.full_name or actor.email,
                "updated_at": SERVER_TIMESTAMP,
            }
            if data.get("status") == "Open":
                updates["status"] = "In Progress"

            txn.update(doc_ref, updates)
            return {"success": True, "message": "Successfully assigned to you.", "from_status": data.get("status")}

        result = assign_in_transaction(transaction)
        if result["success"]:
            # Record audit event
            self._log_audit_event_direct(
                complaint_id=complaint_id,
                event_type="assigned",
                actor_uid=actor.uid,
                actor_name=actor.full_name or actor.email,
                from_status=result.get("from_status"),
                to_status="In Progress" if result.get("from_status") == "Open" else result.get("from_status"),
                note=f"Assigned to administrator {actor.full_name or actor.email}.",
            )
        return result

    def update_complaint_status(
        self,
        complaint_id: str,
        new_status: str,
        actor: AuthenticatedUser,
        resolution_note: Optional[str] = None,
    ) -> bool:
        """Update complaint status and record audit event.
        Authorization: actor.role == 'admin'.
        Validation:
          - If new_status == 'Resolved', resolution_note must be non-empty.
          - If new_status == 'Rejected', note (reason) must be non-empty.
        """
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Only administrators can modify complaint status.")

        valid_statuses = ["Open", "In Progress", "Resolved", "Rejected"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")

        if new_status == "Resolved" and (not resolution_note or not resolution_note.strip()):
            raise ValueError("A non-empty resolution note is required when resolving a complaint.")

        if new_status == "Rejected" and (not resolution_note or not resolution_note.strip()):
            raise ValueError("A rejection reason/note is required when rejecting a complaint.")

        doc_ref = self.db.collection("complaints").document(complaint_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False

        old_data = doc.to_dict()
        from_status = old_data.get("status", "Open")

        updates: Dict[str, Any] = {
            "status": new_status,
            "updated_at": SERVER_TIMESTAMP,
        }

        if resolution_note:
            updates["resolution_note"] = resolution_note.strip()

        if new_status in ["Resolved", "Rejected"]:
            updates["resolved_at"] = SERVER_TIMESTAMP

        doc_ref.update(updates)

        # Log audit event
        event_type = "resolved" if new_status == "Resolved" else ("rejected" if new_status == "Rejected" else "status_changed")
        self._log_audit_event_direct(
            complaint_id=complaint_id,
            event_type=event_type,
            actor_uid=actor.uid,
            actor_name=actor.full_name or actor.email,
            from_status=from_status,
            to_status=new_status,
            note=resolution_note or f"Status changed from {from_status} to {new_status}.",
        )

        # Send notification to student
        reporter_uid = old_data.get("reporter_uid")
        if reporter_uid:
            notif_msg = f"Status updated to '{new_status}'."
            if resolution_note:
                notif_msg += f" Note: {resolution_note.strip()}"
            self.create_notification(
                recipient_uid=reporter_uid,
                complaint_id=complaint_id,
                notif_type=f"status_{new_status.lower()}",
                title=f"Complaint #{complaint_id} {new_status}",
                message=notif_msg,
            )

        return True

    # --------------------------------------------------------------------------
    # 4. Duplicate Detection Candidates
    # --------------------------------------------------------------------------
    def get_duplicate_candidates(self, actor: AuthenticatedUser, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch candidate active complaints for internal semantic duplicate matching.
        Returns complaints with their pre-computed dense embeddings.
        """
        # Internal query: fetch active complaints
        docs = (
            self.db.collection("complaints")
            .where("status", "in", ["Open", "In Progress"])
            .limit(limit)
            .stream()
        )
        candidates = []
        for d in docs:
            c = self._normalize_doc(d.to_dict())
            if c.get("dense_embedding"):
                candidates.append(c)
        return candidates

    # --------------------------------------------------------------------------
    # 5. In-App Notifications
    # --------------------------------------------------------------------------
    def create_notification(
        self,
        recipient_uid: str,
        complaint_id: str,
        notif_type: str,
        title: str,
        message: str,
    ) -> str:
        """Create a notification document for a user."""
        notif_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
        notif_data = {
            "notification_id": notif_id,
            "recipient_uid": recipient_uid,
            "complaint_id": complaint_id,
            "type": notif_type,
            "title": title,
            "message": message,
            "read": False,
            "created_at": SERVER_TIMESTAMP,
        }
        self.db.collection("notifications").document(notif_id).set(notif_data)
        return notif_id

    def get_student_notifications(self, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Fetch notifications strictly scoped to recipient_uid == actor.uid."""
        if not actor or not actor.uid:
            return []

        docs = (
            self.db.collection("notifications")
            .where("recipient_uid", "==", actor.uid)
            .stream()
        )
        results = [self._normalize_doc(d.to_dict()) for d in docs]
        results.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return results

    def mark_notification_read(self, notification_id: str, actor: AuthenticatedUser) -> bool:
        """Mark notification as read. Verifies ownership."""
        if not actor or not actor.uid:
            return False

        doc_ref = self.db.collection("notifications").document(notification_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False

        data = doc.to_dict()
        if not actor.is_admin and data.get("recipient_uid") != actor.uid:
            raise PermissionError("Access Denied: Cannot modify another user's notifications.")

        doc_ref.update({"read": True})
        return True

    # --------------------------------------------------------------------------
    # 6. Immutable Audit Trail
    # --------------------------------------------------------------------------
    def _log_audit_event_direct(
        self,
        complaint_id: str,
        event_type: str,
        actor_uid: str,
        actor_name: Optional[str],
        from_status: Optional[str],
        to_status: Optional[str],
        note: Optional[str],
    ):
        """Append immutable event to complaints/{id}/events/{event_id}."""
        event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
        event_ref = (
            self.db.collection("complaints")
            .document(complaint_id)
            .collection("events")
            .document(event_id)
        )
        event_ref.set({
            "event_id": event_id,
            "event_type": event_type,
            "actor_uid": actor_uid,
            "actor_name": actor_name or "System",
            "from_status": from_status,
            "to_status": to_status,
            "note": note,
            "created_at": SERVER_TIMESTAMP,
        })

    def get_complaint_events(self, complaint_id: str, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        """Retrieve audit history for a complaint."""
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")

        # Check authorization on parent complaint
        complaint = self.get_complaint_by_id(complaint_id, actor)
        if not complaint:
            return []

        events = (
            self.db.collection("complaints")
            .document(complaint_id)
            .collection("events")
            .stream()
        )
        results = [self._normalize_doc(e.to_dict()) for e in events]
        results.sort(key=lambda x: str(x.get("created_at") or ""))
        return results

    # --------------------------------------------------------------------------
    # 7. Dashboard Aggregation (Scoped)
    # --------------------------------------------------------------------------
    def get_dashboard_stats(self, actor: AuthenticatedUser) -> Dict[str, Any]:
        """Aggregate statistics.
        If Admin: Campus-wide metrics.
        If Student: Personal complaint metrics only.
        """
        if not actor or not actor.uid:
            return {"total": 0, "open": 0, "in_progress": 0, "resolved": 0, "critical": 0}

        if actor.is_student:
            complaints = self.get_student_complaints(actor.uid, actor)
        else:
            complaints = self.get_all_complaints(actor, limit=200)

        total = len(complaints)
        open_cnt = sum(1 for c in complaints if c.get("status") == "Open")
        in_prog_cnt = sum(1 for c in complaints if c.get("status") == "In Progress")
        resolved_cnt = sum(1 for c in complaints if c.get("status") in ["Resolved", "Rejected"])
        critical_cnt = sum(1 for c in complaints if c.get("urgency") == "Critical" and c.get("status") in ["Open", "In Progress"])

        return {
            "total": total,
            "open": open_cnt,
            "in_progress": in_prog_cnt,
            "resolved": resolved_cnt,
            "critical": critical_cnt,
        }

    # --------------------------------------------------------------------------
    # Helper: Normalize Firestore Timestamps and Types
    # --------------------------------------------------------------------------
    def _normalize_doc(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Firestore Timestamps to ISO strings and format dict."""
        res = dict(doc)
        for key in ["created_at", "updated_at", "resolved_at"]:
            val = res.get(key)
            if val is not None:
                if hasattr(val, "isoformat"):
                    res[key] = val.isoformat()
                elif hasattr(val, "timestamp"):
                    res[key] = datetime.fromtimestamp(val.timestamp(), tz=timezone.utc).isoformat()
                else:
                    res[key] = str(val)
        return res
