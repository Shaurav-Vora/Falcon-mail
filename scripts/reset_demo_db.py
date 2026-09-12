"""
SENTINEL - Demo Database Reset Script
Safe utility to intentionally reset database/sentinel.db before demo presentations.

NOTE: This script requires explicit user confirmation before modifying the database.
DO NOT execute without authorization.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_PATH
from database.database import init_db

def reset_demo_database():
    """Reset the demo database to a clean, empty state with initialized schema."""
    print("==========================================================")
    print("          SENTINEL DEMO DATABASE RESET UTILITY            ")
    print("==========================================================")
    print(f"Target Database: {DB_PATH}")
    print("\nWARNING: This will permanently erase all complaint records in the demo DB.")
    
    confirm = input("Type 'RESET' to confirm database wipe: ").strip()
    if confirm != "RESET":
        print("Operation cancelled. Database remains untouched.")
        return False
        
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing database file: {DB_PATH}")
        
    init_db(DB_PATH)
    print("Clean database schema initialized successfully.")
    print("Database is ready for fresh demo submissions.")
    return True

if __name__ == "__main__":
    reset_demo_database()
