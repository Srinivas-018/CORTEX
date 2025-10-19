"""
Database Manager for CORTEX
Handles case management, evidence tracking, and chain of custody
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "cortex.db"

def init_database():
    """Initialize the CORTEX database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            case_name TEXT NOT NULL,
            investigator TEXT,
            device_info TEXT,
            image_path TEXT,
            image_hash TEXT,
            created_date TEXT,
            status TEXT DEFAULT 'Open',
            notes TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            artifact_type TEXT,
            artifact_name TEXT,
            file_path TEXT,
            hash_value TEXT,
            timestamp TEXT,
            metadata TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chain_of_custody (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            action TEXT,
            performed_by TEXT,
            timestamp TEXT,
            details TEXT,
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        )
    """)
    
    conn.commit()
    conn.close()

def create_case(case_id, case_name, investigator, device_info="", notes=""):
    """Create a new forensic case"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO cases (case_id, case_name, investigator, device_info, created_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (case_id, case_name, investigator, device_info, datetime.now().isoformat(), notes))
        
        conn.commit()
        conn.close()
        
        add_chain_of_custody(case_id, "Case Created", investigator, f"Created case: {case_name}")
        
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_all_cases():
    """Retrieve all cases"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM cases ORDER BY created_date DESC")
    cases = cursor.fetchall()
    conn.close()
    
    return cases

def get_case(case_id):
    """Get a specific case by ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
    case = cursor.fetchone()
    conn.close()
    
    return case

def update_case(case_id, **kwargs):
    """Update case information"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for key, value in kwargs.items():
        cursor.execute(f"UPDATE cases SET {key} = ? WHERE case_id = ?", (value, case_id))
    
    conn.commit()
    conn.close()

def delete_case(case_id):
    """Delete a case and all associated evidence"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM evidence WHERE case_id = ?", (case_id,))
    cursor.execute("DELETE FROM chain_of_custody WHERE case_id = ?", (case_id,))
    cursor.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
    
    conn.commit()
    conn.close()

def add_evidence(case_id, artifact_type, artifact_name, file_path="", hash_value="", metadata=None):
    """Add evidence to a case"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO evidence (case_id, artifact_type, artifact_name, file_path, hash_value, timestamp, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (case_id, artifact_type, artifact_name, file_path, hash_value, 
          datetime.now().isoformat(), json.dumps(metadata) if metadata else "{}"))
    
    conn.commit()
    conn.close()

def get_case_evidence(case_id):
    """Get all evidence for a case"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM evidence WHERE case_id = ? ORDER BY timestamp DESC", (case_id,))
    evidence = cursor.fetchall()
    conn.close()
    
    return evidence

def add_chain_of_custody(case_id, action, performed_by, details=""):
    """Add a chain of custody log entry"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO chain_of_custody (case_id, action, performed_by, timestamp, details)
        VALUES (?, ?, ?, ?, ?)
    """, (case_id, action, performed_by, datetime.now().isoformat(), details))
    
    conn.commit()
    conn.close()

def get_chain_of_custody(case_id):
    """Get chain of custody log for a case"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM chain_of_custody WHERE case_id = ? ORDER BY timestamp ASC", (case_id,))
    logs = cursor.fetchall()
    conn.close()
    
    return logs

init_database()
