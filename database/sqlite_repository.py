"""
SENTINEL - SQLite Repository Implementation
Provides isolated local persistence for unit tests and local offline development.
Implements the BaseComplaintRepository interface with full server-side RBAC validation.
Guarantees clean connection teardown to prevent Windows file locking issues in tests.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

import config
from database.auth_context import AuthenticatedUser
from database.base_repository import BaseComplaintRepository

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


class SQLiteRepository(BaseComplaintRepository):
    """SQLite implementation of BaseComplaintRepository for tests and offline usage."""

    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _conn(self):
        """Context manager yielding connection and guaranteeing close in finally."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self):
        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                category TEXT,
                category_confidence REAL,
                urgency TEXT,
                urgency_confidence REAL,
                department TEXT,
                location TEXT,
                building TEXT,
                room TEXT,
                status TEXT DEFAULT 'Open',
                reporter_uid TEXT,
                reporter_name TEXT,
                reporter_email TEXT,
                student_id TEXT,
                programme TEXT,
                assigned_admin_uid TEXT,
                assigned_admin_name TEXT,
                resolution_note TEXT,
                dense_embedding BLOB,
                duplicate_of_id TEXT,
                duplicate_similarity REAL,
                entities_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaint_events (
                event_id TEXT PRIMARY KEY,
                complaint_id TEXT,
                event_type TEXT,
                actor_uid TEXT,
                actor_name TEXT,
                from_status TEXT,
                to_status TEXT,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                recipient_uid TEXT,
                complaint_id TEXT,
                type TEXT,
                title TEXT,
                message TEXT,
                read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.commit()

    def create_complaint(self, data: Dict[str, Any], actor: AuthenticatedUser) -> str:
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")

        complaint_id = data.get("complaint_id") or f"CMP-{uuid.uuid4().hex[:8].upper()}"
        embedding_blob = None
        if data.get("dense_embedding") is not None:
            arr = np.array(data["dense_embedding"], dtype=np.float32)
            embedding_blob = sqlite3.Binary(arr.tobytes())

        entities_json = json.dumps(data.get("entities", {}))

        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO complaints (
                id, title, description, category, category_confidence, urgency, urgency_confidence,
                department, location, building, room, status, reporter_uid, reporter_name,
                reporter_email, student_id, programme, assigned_admin_uid, assigned_admin_name,
                resolution_note, dense_embedding, duplicate_of_id, duplicate_similarity,
                entities_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                complaint_id,
                data.get("title", "Untitled Complaint"),
                data.get("description", ""),
                data.get("category", "Other"),
                float(data.get("category_confidence", 1.0)),
                data.get("urgency", "Medium"),
                float(data.get("urgency_confidence", 1.0)),
                data.get("department", "General Services"),
                data.get("location", "Campus"),
                data.get("building"),
                data.get("room"),
                "Open",
                actor.uid,
                actor.full_name,
                actor.email,
                actor.student_id or data.get("student_id"),
                actor.programme or data.get("programme"),
                None,
                None,
                None,
                embedding_blob,
                data.get("duplicate_of_id"),
                float(data.get("duplicate_similarity", 0.0)) if data.get("duplicate_similarity") is not None else None,
                entities_json
            ))

            # Audit event
            event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("""
            INSERT INTO complaint_events (
                event_id, complaint_id, event_type, actor_uid, actor_name, from_status, to_status, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, complaint_id, "submitted", actor.uid, actor.full_name, None, "Open", "Complaint submitted."
            ))

            # Notification
            notif_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("""
            INSERT INTO notifications (
                notification_id, recipient_uid, complaint_id, type, title, message
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                notif_id, actor.uid, complaint_id, "complaint_created", "Complaint Submitted",
                f"Your complaint #{complaint_id} has been registered."
            ))
            conn.commit()

        return complaint_id

    def get_complaint_by_id(self, complaint_id: str, actor: AuthenticatedUser) -> Optional[Dict[str, Any]]:
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")

        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,))
            row = cursor.fetchone()
            if not row:
                return None
            doc = self._row_to_dict(row)
            if not actor.is_admin and doc.get("reporter_uid") != actor.uid:
                raise PermissionError("Access Denied: You do not have permission to view this complaint.")
            return doc

    def get_student_complaints(self, uid: str, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")
        if not actor.is_admin and actor.uid != uid:
            raise PermissionError("Access Denied: Students can only access their own complaints.")

        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM complaints WHERE reporter_uid = ? ORDER BY created_at DESC", (uid,))
            return [self._row_to_dict(r) for r in cursor.fetchall()]

    def get_all_complaints(self, actor: AuthenticatedUser, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Admin privileges required.")

        query = "SELECT * FROM complaints ORDER BY created_at DESC"
        params: List[Any] = []
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_dict(r) for r in cursor.fetchall()]

    def get_unresolved_complaints(self, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Admin privileges required.")

        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM complaints WHERE status IN ('Open', 'In Progress')")
            results = [self._row_to_dict(r) for r in cursor.fetchall()]

        results.sort(key=lambda x: (PRIORITY_ORDER.get(x.get("urgency", "Medium"), 2), str(x.get("created_at") or "")))
        return results

    def get_recent_complaints(self, actor: AuthenticatedUser, limit: int = 50) -> List[Dict[str, Any]]:
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Admin privileges required.")

        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC LIMIT ?", (limit,))
            return [self._row_to_dict(r) for r in cursor.fetchall()]

    def get_resolved_cases(self, actor: AuthenticatedUser, limit: int = 50) -> List[Dict[str, Any]]:
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Admin privileges required.")

        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM complaints WHERE status IN ('Resolved', 'Rejected') ORDER BY updated_at DESC LIMIT ?", (limit,))
            return [self._row_to_dict(r) for r in cursor.fetchall()]

    def assign_complaint(self, complaint_id: str, actor: AuthenticatedUser) -> Dict[str, Any]:
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Only administrators can assign complaints.")

        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT assigned_admin_uid, assigned_admin_name, status FROM complaints WHERE id = ?", (complaint_id,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "message": "Complaint not found."}

            if row["assigned_admin_uid"] and row["assigned_admin_uid"] != actor.uid:
                return {
                    "success": False,
                    "message": f"Already claimed by administrator: {row['assigned_admin_name']}",
                    "already_assigned": True,
                }

            from_status = row["status"]
            new_status = "In Progress" if from_status == "Open" else from_status
            cursor.execute("""
            UPDATE complaints
            SET assigned_admin_uid = ?, assigned_admin_name = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (actor.uid, actor.full_name or actor.email, new_status, complaint_id))

            # Audit event
            event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("""
            INSERT INTO complaint_events (
                event_id, complaint_id, event_type, actor_uid, actor_name, from_status, to_status, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, complaint_id, "assigned", actor.uid, actor.full_name or actor.email,
                from_status, new_status, f"Assigned to administrator {actor.full_name or actor.email}."
            ))
            conn.commit()

        return {"success": True, "message": "Successfully assigned to you."}

    def update_complaint_status(
        self,
        complaint_id: str,
        new_status: str,
        actor: AuthenticatedUser,
        resolution_note: Optional[str] = None,
    ) -> bool:
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Only administrators can modify complaint status.")

        valid_statuses = ["Open", "In Progress", "Resolved", "Rejected"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")

        if new_status == "Resolved" and (not resolution_note or not resolution_note.strip()):
            raise ValueError("A non-empty resolution note is required when resolving a complaint.")

        if new_status == "Rejected" and (not resolution_note or not resolution_note.strip()):
            raise ValueError("A rejection reason/note is required when rejecting a complaint.")

        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, reporter_uid FROM complaints WHERE id = ?", (complaint_id,))
            row = cursor.fetchone()
            if not row:
                return False

            from_status = row["status"]
            reporter_uid = row["reporter_uid"]

            cursor.execute("""
            UPDATE complaints
            SET status = ?, resolution_note = ?, updated_at = CURRENT_TIMESTAMP,
                resolved_at = CASE WHEN ? IN ('Resolved', 'Rejected') THEN CURRENT_TIMESTAMP ELSE resolved_at END
            WHERE id = ?
            """, (new_status, resolution_note.strip() if resolution_note else None, new_status, complaint_id))

            # Audit event
            event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
            event_type = "resolved" if new_status == "Resolved" else ("rejected" if new_status == "Rejected" else "status_changed")
            cursor.execute("""
            INSERT INTO complaint_events (
                event_id, complaint_id, event_type, actor_uid, actor_name, from_status, to_status, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, complaint_id, event_type, actor.uid, actor.full_name or actor.email,
                from_status, new_status, resolution_note or f"Status changed from {from_status} to {new_status}."
            ))

            # Notification
            if reporter_uid:
                notif_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
                notif_msg = f"Status updated to '{new_status}'."
                if resolution_note:
                    notif_msg += f" Note: {resolution_note.strip()}"
                cursor.execute("""
                INSERT INTO notifications (
                    notification_id, recipient_uid, complaint_id, type, title, message
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    notif_id, reporter_uid, complaint_id, f"status_{new_status.lower()}",
                    f"Complaint #{complaint_id} {new_status}", notif_msg
                ))

            conn.commit()
            return True

    def get_duplicate_candidates(self, actor: AuthenticatedUser, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM complaints WHERE status IN ('Open', 'In Progress') LIMIT ?", (limit,))
            candidates = []
            for r in cursor.fetchall():
                d = self._row_to_dict(r)
                if d.get("dense_embedding") is not None:
                    candidates.append(d)
            return candidates

    def create_notification(self, recipient_uid: str, complaint_id: str, notif_type: str, title: str, message: str) -> str:
        notif_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO notifications (notification_id, recipient_uid, complaint_id, type, title, message)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (notif_id, recipient_uid, complaint_id, notif_type, title, message))
            conn.commit()
        return notif_id

    def get_student_notifications(self, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        if not actor or not actor.uid:
            return []
        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notifications WHERE recipient_uid = ? ORDER BY created_at DESC", (actor.uid,))
            return [dict(r) for r in cursor.fetchall()]

    def mark_notification_read(self, notification_id: str, actor: AuthenticatedUser) -> bool:
        if not actor or not actor.uid:
            return False
        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT recipient_uid FROM notifications WHERE notification_id = ?", (notification_id,))
            row = cursor.fetchone()
            if not row:
                return False
            if not actor.is_admin and row["recipient_uid"] != actor.uid:
                raise PermissionError("Access Denied: Cannot modify another user's notifications.")
            cursor.execute("UPDATE notifications SET read = 1 WHERE notification_id = ?", (notification_id,))
            conn.commit()
            return True

    def get_complaint_events(self, complaint_id: str, actor: AuthenticatedUser) -> List[Dict[str, Any]]:
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")
        complaint = self.get_complaint_by_id(complaint_id, actor)
        if not complaint:
            return []
        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM complaint_events WHERE complaint_id = ? ORDER BY created_at ASC", (complaint_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_dashboard_stats(self, actor: AuthenticatedUser) -> Dict[str, Any]:
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

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["complaint_id"] = d.get("id")
        if d.get("dense_embedding"):
            d["dense_embedding"] = np.frombuffer(d["dense_embedding"], dtype=np.float32).tolist()
        if d.get("entities_json"):
            try:
                d["entities"] = json.loads(d["entities_json"])
            except Exception:
                d["entities"] = {}
        return d
