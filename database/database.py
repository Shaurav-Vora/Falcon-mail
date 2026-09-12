import os
import sys
import sqlite3
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_PATH

ALLOWED_STATUSES = {"Open", "In Progress", "Resolved", "Rejected"}

def get_db_connection(db_path: str = DB_PATH):
    """Create a database connection to SQLite with row_factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DB_PATH):
    """Initialize SQLite database schema for SENTINEL complaints with safe schema migrations."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_text TEXT NOT NULL,
            processed_text TEXT,
            category TEXT NOT NULL,
            category_confidence REAL,
            urgency TEXT NOT NULL,
            urgency_confidence REAL,
            rule_elevated INTEGER DEFAULT 0,
            location TEXT,
            user_location TEXT,
            user_category TEXT,
            date_entity TEXT,
            time_entity TEXT,
            issue TEXT,
            summary TEXT,
            recommended_department TEXT,
            is_duplicate INTEGER DEFAULT 0,
            duplicate_of_id INTEGER,
            duplicate_similarity REAL,
            status TEXT DEFAULT 'Open',
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Check if user_location and user_category columns exist (for migration)
        cursor.execute("PRAGMA table_info(complaints);")
        columns = [row["name"] for row in cursor.fetchall()]
        
        if "user_location" not in columns:
            cursor.execute("ALTER TABLE complaints ADD COLUMN user_location TEXT;")
        if "user_category" not in columns:
            cursor.execute("ALTER TABLE complaints ADD COLUMN user_category TEXT;")
            
        conn.commit()
    finally:
        conn.close()

def insert_complaint(data: dict, db_path: str = DB_PATH) -> int:
    """Insert a new complaint and NLP analysis record into SQLite DB safely."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        
        # Serialize embedding vector to binary BLOB
        embedding_blob = None
        if "embedding" in data and data["embedding"] is not None:
            emb_arr = np.array(data["embedding"], dtype=np.float32)
            embedding_blob = sqlite3.Binary(emb_arr.tobytes())
            
        dup_info = data.get("duplicate", {})
        entities = data.get("entities", {})
        
        # Status validation
        status = data.get("status", "Open")
        if status not in ALLOWED_STATUSES:
            status = "Open"
        
        cursor.execute("""
        INSERT INTO complaints (
            complaint_text, processed_text, category, category_confidence,
            urgency, urgency_confidence, rule_elevated, location, user_location, user_category,
            date_entity, time_entity, issue, summary, recommended_department,
            is_duplicate, duplicate_of_id, duplicate_similarity, status, embedding
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("original_text", ""),
            data.get("processed_text", ""),
            data.get("category", "Other"),
            data.get("category_confidence", 0.0),
            data.get("urgency", "Low"),
            data.get("urgency_confidence", 0.0),
            1 if data.get("rule_elevated") else 0,
            entities.get("location", "Not specified"),
            data.get("user_location"),
            data.get("user_category"),
            entities.get("date"),
            entities.get("time"),
            data.get("issue"),
            data.get("summary"),
            data.get("recommended_department"),
            1 if dup_info.get("is_duplicate") else 0,
            dup_info.get("matched_id"),
            dup_info.get("similarity", 0.0),
            status,
            embedding_blob
        ))
        
        complaint_id = cursor.lastrowid
        conn.commit()
        return complaint_id
    finally:
        conn.close()

def get_all_complaints(db_path: str = DB_PATH) -> list[dict]:
    """Retrieve all complaints from SQLite DB formatted as dictionary list."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, complaint_text, category, category_confidence, urgency, urgency_confidence, 
               rule_elevated, location, user_location, user_category, issue, summary, 
               recommended_department, is_duplicate, duplicate_of_id, duplicate_similarity, 
               status, embedding, created_at
        FROM complaints
        ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        complaints = []
        for r in rows:
            item = dict(r)
            if item.get("embedding"):
                item["embedding"] = np.frombuffer(item["embedding"], dtype=np.float32)
            item["text"] = item["complaint_text"]
            complaints.append(item)
            
        return complaints
    finally:
        conn.close()

def update_complaint_status(complaint_id: int, new_status: str, db_path: str = DB_PATH) -> bool:
    """
    Update status of a complaint with strict validation.
    Allowed statuses: 'Open', 'In Progress', 'Resolved', 'Rejected'.
    """
    if new_status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Allowed values: {sorted(list(ALLOWED_STATUSES))}")
        
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE complaints
        SET status = ?
        WHERE id = ?
        """, (new_status, complaint_id))
        
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    records = get_all_complaints()
    print(f"Total existing database records: {len(records)}")
