import os
import sys
import sqlite3
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_PATH

def get_db_connection():
    """Create a database connection to SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database schema for SENTINEL complaints."""
    conn = get_db_connection()
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
    
    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")

def insert_complaint(data: dict) -> int:
    """Insert a new complaint and NLP analysis record into SQLite DB."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Serialize embedding vector to binary BLOB
    embedding_blob = None
    if "embedding" in data and data["embedding"] is not None:
        emb_arr = np.array(data["embedding"], dtype=np.float32)
        embedding_blob = sqlite3.Binary(emb_arr.tobytes())
        
    dup_info = data.get("duplicate", {})
    entities = data.get("entities", {})
    
    cursor.execute("""
    INSERT INTO complaints (
        complaint_text, processed_text, category, category_confidence,
        urgency, urgency_confidence, rule_elevated, location,
        date_entity, time_entity, issue, summary, recommended_department,
        is_duplicate, duplicate_of_id, duplicate_similarity, status, embedding
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("original_text", ""),
        data.get("processed_text", ""),
        data.get("category", "Other"),
        data.get("category_confidence", 0.0),
        data.get("urgency", "Low"),
        data.get("urgency_confidence", 0.0),
        1 if data.get("rule_elevated") else 0,
        entities.get("location", "Not specified"),
        entities.get("date"),
        entities.get("time"),
        data.get("issue"),
        data.get("summary"),
        data.get("recommended_department"),
        1 if dup_info.get("is_duplicate") else 0,
        dup_info.get("matched_id"),
        dup_info.get("similarity", 0.0),
        data.get("status", "Open"),
        embedding_blob
    ))
    
    complaint_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return complaint_id

def get_all_complaints() -> list[dict]:
    """Retrieve all complaints from SQLite DB formatted as dictionary list."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, complaint_text, category, category_confidence, urgency, urgency_confidence, 
           rule_elevated, location, issue, summary, recommended_department, is_duplicate, 
           duplicate_of_id, duplicate_similarity, status, embedding, created_at
    FROM complaints
    ORDER BY created_at DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    complaints = []
    for r in rows:
        item = dict(r)
        # Deserialize embedding BLOB
        if item.get("embedding"):
            item["embedding"] = np.frombuffer(item["embedding"], dtype=np.float32)
        item["text"] = item["complaint_text"]
        complaints.append(item)
        
    return complaints

def update_complaint_status(complaint_id: int, new_status: str) -> bool:
    """Update status of a complaint (Open, In Progress, Resolved, Rejected)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE complaints
    SET status = ?
    WHERE id = ?
    """, (new_status, complaint_id))
    
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

if __name__ == "__main__":
    init_db()
    records = get_all_complaints()
    print(f"Total existing database records: {len(records)}")
