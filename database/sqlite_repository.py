"""
Falcon Mail - SQLite Repository Implementation
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
from database.identifiers import generate_complaint_id, generate_processing_run_id

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

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_runs (
                run_id TEXT PRIMARY KEY,
                ticket_id TEXT,
                reporter_uid TEXT,
                reporter_name TEXT,
                title TEXT,
                submitted_location TEXT,
                overall_status TEXT,
                current_stage TEXT,
                stages_json TEXT,
                retry_count INTEGER DEFAULT 0,
                attempt_history_json TEXT,
                safe_error TEXT,
                diagnostic_code TEXT,
                created_at TEXT,
                updated_at TEXT,
                completed_at TEXT
            );
            """)

            cursor.execute("PRAGMA table_info(complaints)")
            complaint_columns = {row[1] for row in cursor.fetchall()}
            trace_columns = {
                "processing_run_id": "TEXT",
                "processing_status": "TEXT",
                "needs_manual_review": "INTEGER DEFAULT 0",
                "model_versions_json": "TEXT",
                "prediction_overrides_json": "TEXT",
                "safe_error": "TEXT",
                "diagnostic_code": "TEXT",
            }
            for column_name, column_type in trace_columns.items():
                if column_name not in complaint_columns:
                    cursor.execute(
                        f"ALTER TABLE complaints ADD COLUMN {column_name} {column_type}"
                    )
            conn.commit()

    def create_complaint(self, data: Dict[str, Any], actor: AuthenticatedUser) -> str:
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")

        complaint_id = data.get("complaint_id") or generate_complaint_id()
        embedding_blob = None
        if data.get("dense_embedding") is not None:
            arr = np.array(data["dense_embedding"], dtype=np.float32)
            embedding_blob = sqlite3.Binary(arr.tobytes())

        entities = data["entities"] if "entities" in data else {}
        entities_json = json.dumps(entities)
        model_versions_json = json.dumps(data.get("model_versions", {}))
        prediction_overrides_json = json.dumps(data.get("prediction_overrides", []))

        with self._conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO complaints (
                id, title, description, category, category_confidence, urgency, urgency_confidence,
                department, location, building, room, status, reporter_uid, reporter_name,
                reporter_email, student_id, programme, assigned_admin_uid, assigned_admin_name,
                resolution_note, dense_embedding, duplicate_of_id, duplicate_similarity,
                entities_json, processing_run_id, processing_status, needs_manual_review,
                model_versions_json, prediction_overrides_json, safe_error, diagnostic_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                complaint_id,
                data.get("title", "Untitled Complaint"),
                data.get("description", ""),
                data["category"] if "category" in data else "Other",
                self._optional_float(data, "category_confidence", 1.0),
                data["urgency"] if "urgency" in data else "Medium",
                self._optional_float(data, "urgency_confidence", 1.0),
                data["department"] if "department" in data else "General Services",
                data.get("location", "Campus"),
                data.get("building"),
                data.get("room"),
                data.get("status", "Open"),
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
                entities_json,
                data.get("processing_run_id"),
                data.get("processing_status"),
                int(bool(data.get("needs_manual_review", False))),
                model_versions_json,
                prediction_overrides_json,
                data.get("safe_error"),
                data.get("diagnostic_code"),
            ))

            # Audit event
            event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("""
            INSERT INTO complaint_events (
                event_id, complaint_id, event_type, actor_uid, actor_name, from_status, to_status, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, complaint_id, "submitted", actor.uid, actor.full_name, None,
                data.get("status", "Open"), "Complaint submitted."
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

    def create_processing_run(self, run: Dict[str, Any], actor: AuthenticatedUser) -> str:
        """Create an authorized NLP processing run in offline storage."""
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")

        reporter_uid = run.get("reporter_uid") or actor.uid
        if not actor.is_admin and reporter_uid != actor.uid:
            raise PermissionError("Access Denied: Cannot create another student's processing run.")

        run_id = run.get("run_id") or generate_processing_run_id()
        now = self._utc_now()
        with self._conn() as conn:
            conn.execute("""
            INSERT INTO processing_runs (
                run_id, ticket_id, reporter_uid, reporter_name, title, submitted_location,
                overall_status, current_stage, stages_json, retry_count,
                attempt_history_json, safe_error, diagnostic_code, created_at, updated_at,
                completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                run.get("ticket_id") or run.get("complaint_id"),
                reporter_uid,
                run.get("reporter_name") or actor.full_name,
                run.get("title", "Untitled Complaint"),
                run.get("submitted_location"),
                "processing",
                "received",
                json.dumps({}),
                0,
                json.dumps([]),
                None,
                None,
                now,
                now,
                None,
            ))
            conn.commit()
        return run_id

    def update_processing_stage(
        self,
        run_id: str,
        stage: str,
        data: Dict[str, Any],
        actor: AuthenticatedUser,
    ) -> None:
        """Persist a stage payload after owner/admin authorization."""
        run = self._authorized_processing_run(run_id, actor)
        stages = run.get("stages", {})
        stages[stage] = data
        with self._conn() as conn:
            conn.execute("""
            UPDATE processing_runs
            SET current_stage = ?, stages_json = ?, updated_at = ?
            WHERE run_id = ?
            """, (stage, json.dumps(stages), self._utc_now(), run_id))
            conn.commit()

    def finish_processing_run(
        self,
        run_id: str,
        status: str,
        data: Dict[str, Any],
        actor: AuthenticatedUser,
    ) -> None:
        """Finish a run while preserving its immutable owner and identity."""
        if status not in {"processing", "completed", "failed", "needs_review"}:
            raise ValueError(
                "Processing run status must be processing, completed, failed, or needs_review."
            )
        run = self._authorized_processing_run(run_id, actor)
        now = self._utc_now()
        stages = data.get("stages", run.get("stages", {}))
        attempt_history = data.get("attempt_history", run.get("attempt_history", []))
        with self._conn() as conn:
            conn.execute("""
            UPDATE processing_runs
            SET overall_status = ?, current_stage = ?, stages_json = ?, retry_count = ?,
                attempt_history_json = ?, safe_error = ?, diagnostic_code = ?,
                updated_at = ?, completed_at = ?
            WHERE run_id = ?
            """, (
                status,
                data.get("current_stage", run.get("current_stage")),
                json.dumps(stages),
                int(data.get("retry_count", run.get("retry_count", 0))),
                json.dumps(attempt_history),
                data.get("safe_error"),
                data.get("diagnostic_code"),
                now,
                None if status == "processing" else now,
                run_id,
            ))
            conn.commit()

    def get_processing_run(
        self,
        run_id: str,
        actor: AuthenticatedUser,
    ) -> Optional[Dict[str, Any]]:
        """Return a full administrator trace or sanitized owner progress."""
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM processing_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if not row:
            return None
        run = self._processing_row_to_dict(row)
        if not actor.is_admin and run.get("reporter_uid") != actor.uid:
            raise PermissionError("Access Denied: Cannot view another student's processing run.")
        return run if actor.is_admin else self._strip_trace_diagnostics(run)

    def list_processing_runs(
        self,
        actor: AuthenticatedUser,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List newest-updated processing runs for administrators."""
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Admin privileges required.")
        safe_limit = max(1, min(int(limit), 500))
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM processing_runs ORDER BY updated_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [self._processing_row_to_dict(row) for row in rows]

    def finalize_complaint_analysis(
        self,
        complaint_id: str,
        data: Dict[str, Any],
        actor: AuthenticatedUser,
    ) -> None:
        """Persist supported NLP results on an existing complaint."""
        self._authorized_complaint(complaint_id, actor)
        embedding_blob = None
        if data.get("dense_embedding") is not None:
            embedding = np.array(data["dense_embedding"], dtype=np.float32)
            embedding_blob = sqlite3.Binary(embedding.tobytes())
        entities_json = json.dumps(data.get("entities", {}))
        model_versions_json = json.dumps(data.get("model_versions", {}))

        with self._conn() as conn:
            conn.execute("""
            UPDATE complaints
            SET title = ?, category = ?, category_confidence = ?, urgency = ?,
                urgency_confidence = ?, department = ?, location = ?, building = ?, room = ?,
                dense_embedding = ?, duplicate_of_id = ?, duplicate_similarity = ?,
                entities_json = ?, processing_run_id = ?, processing_status = 'completed',
                needs_manual_review = 0, model_versions_json = ?, safe_error = NULL,
                diagnostic_code = NULL, status = 'Open', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (
                data.get("title"),
                data.get("category"),
                data.get("category_confidence"),
                data.get("urgency") or data.get("final_urgency"),
                data.get("urgency_confidence"),
                data.get("department") or data.get("recommended_department"),
                data.get("location"),
                data.get("building"),
                data.get("room"),
                embedding_blob,
                data.get("duplicate_of_id"),
                data.get("duplicate_similarity"),
                entities_json,
                data.get("processing_run_id"),
                model_versions_json,
                complaint_id,
            ))
            conn.commit()

    def mark_complaint_needs_review(
        self,
        complaint_id: str,
        safe_error: str,
        diagnostic_code: str,
        actor: AuthenticatedUser,
    ) -> None:
        """Retain a failed ticket without invented analysis values."""
        self._authorized_complaint(complaint_id, actor)
        with self._conn() as conn:
            conn.execute("""
            UPDATE complaints
            SET status = 'Needs Review', category = NULL, category_confidence = NULL,
                urgency = NULL, urgency_confidence = NULL, department = NULL,
                processing_status = 'needs_review', needs_manual_review = 1,
                safe_error = ?, diagnostic_code = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (safe_error, diagnostic_code, complaint_id))
            conn.commit()

    def override_complaint_prediction(
        self,
        complaint_id: str,
        field: str,
        new_value: Any,
        reason: str,
        actor: AuthenticatedUser,
    ) -> None:
        """Apply and audit an administrator prediction correction."""
        if not actor or not actor.is_admin:
            raise PermissionError("Access Denied: Admin privileges required.")
        if field not in {"category", "urgency", "location", "department"}:
            raise ValueError("Only category, urgency, location, and department may be overridden.")
        if not reason or not reason.strip():
            raise ValueError("A non-empty reason is required for prediction overrides.")

        complaint = self._authorized_complaint(complaint_id, actor)
        overrides = complaint.get("prediction_overrides", [])
        overrides.append({
            "field": field,
            "previous_value": complaint.get(field),
            "new_value": new_value,
            "administrator_uid": actor.uid,
            "administrator_name": actor.full_name or actor.email,
            "reason": reason.strip(),
            "created_at": self._utc_now(),
        })
        event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
        with self._conn() as conn:
            conn.execute(
                f"UPDATE complaints SET {field} = ?, prediction_overrides_json = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_value, json.dumps(overrides), complaint_id),
            )
            conn.execute("""
            INSERT INTO complaint_events (
                event_id, complaint_id, event_type, actor_uid, actor_name,
                from_status, to_status, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                complaint_id,
                "prediction_overridden",
                actor.uid,
                actor.full_name or actor.email,
                complaint.get("status"),
                complaint.get("status"),
                f"{field} corrected: {reason.strip()}",
            ))
            conn.commit()

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

    def _authorized_processing_run(
        self,
        run_id: str,
        actor: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Return a processing run after owner/admin authorization."""
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM processing_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if not row:
            raise ValueError(f"Processing run '{run_id}' was not found.")
        run = self._processing_row_to_dict(row)
        if not actor.is_admin and run.get("reporter_uid") != actor.uid:
            raise PermissionError("Access Denied: Cannot modify another student's processing run.")
        return run

    def _authorized_complaint(
        self,
        complaint_id: str,
        actor: AuthenticatedUser,
    ) -> Dict[str, Any]:
        """Return a complaint after owner/admin authorization."""
        if not actor or not actor.uid:
            raise PermissionError("Unauthenticated request.")
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM complaints WHERE id = ?", (complaint_id,)
            ).fetchone()
        if not row:
            raise ValueError(f"Complaint '{complaint_id}' was not found.")
        complaint = self._row_to_dict(row)
        if not actor.is_admin and complaint.get("reporter_uid") != actor.uid:
            raise PermissionError("Access Denied: Cannot modify another student's complaint.")
        return complaint

    @staticmethod
    def _processing_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """Deserialize JSON fields from one processing-run row."""
        run = dict(row)
        for source, target, default in (
            ("stages_json", "stages", {}),
            ("attempt_history_json", "attempt_history", []),
        ):
            try:
                run[target] = json.loads(run.get(source) or json.dumps(default))
            except (TypeError, json.JSONDecodeError):
                run[target] = default
            run.pop(source, None)
        return run

    @staticmethod
    def _strip_trace_diagnostics(value: Any) -> Any:
        """Recursively remove administrator-only evidence and diagnostics."""
        private_keys = {"evidence", "safe_error", "diagnostic_code"}
        if isinstance(value, dict):
            return {
                key: SQLiteRepository._strip_trace_diagnostics(item)
                for key, item in value.items()
                if key not in private_keys
            }
        if isinstance(value, list):
            return [SQLiteRepository._strip_trace_diagnostics(item) for item in value]
        return value

    @staticmethod
    def _optional_float(data: Dict[str, Any], key: str, default: float) -> Optional[float]:
        """Coerce a numeric field while preserving an explicitly supplied null."""
        value = data[key] if key in data else default
        return None if value is None else float(value)

    @staticmethod
    def _utc_now() -> str:
        """Return an orderable UTC timestamp for SQLite trace records."""
        return datetime.now(timezone.utc).isoformat()

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
        for source, target, default in (
            ("model_versions_json", "model_versions", {}),
            ("prediction_overrides_json", "prediction_overrides", []),
        ):
            if source in d:
                try:
                    d[target] = json.loads(d.get(source) or json.dumps(default))
                except (TypeError, json.JSONDecodeError):
                    d[target] = default
        if "needs_manual_review" in d:
            d["needs_manual_review"] = bool(d["needs_manual_review"])
        return d
