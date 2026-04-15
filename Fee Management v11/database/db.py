"""
Database module v3
Full schema with: auth, audit log, cancellations, daily report, re-admissions
PyInstaller-compatible with configurable DB path.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "database", "school_fees.db")

def set_db_path(path):
    """Called by app.py to set writable path when running as exe"""
    global DB_PATH
    DB_PATH = path
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    conn = get_db()
    try:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                display_name TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                last_login TEXT)""")

        if not c.execute("SELECT 1 FROM users").fetchone():
            users = [
                ('management', generate_password_hash('Mgmt@2026'), 'management', 'Management'),
                ('admin1',     generate_password_hash('Admin1@2026'), 'admin', 'Admin One'),
                ('admin2',     generate_password_hash('Admin2@2026'), 'admin', 'Admin Two'),
            ]
            c.executemany("INSERT INTO users (username, password_hash, role, display_name) VALUES (?,?,?,?)", users)

        c.execute("""CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_of_admission TEXT,
                sl_no INTEGER,
                student_name TEXT NOT NULL,
                class TEXT,
                section TEXT DEFAULT '',
                reference_no TEXT UNIQUE,
                father_name TEXT NOT NULL,
                mother_name TEXT NOT NULL,
                father_contact TEXT DEFAULT '',
                mother_contact TEXT DEFAULT '',
                status TEXT DEFAULT 'Not Admitted',
                gross_tuition REAL DEFAULT 0,
                concession REAL DEFAULT 0,
                net_tuition REAL DEFAULT 0,
                misc_to_pay REAL DEFAULT 0,
                neft_paid REAL DEFAULT 0,
                cash_paid REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                comments TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime')))""")

        c.execute("""CREATE TABLE IF NOT EXISTS counters (
                name TEXT PRIMARY KEY, value INTEGER DEFAULT 0)""")
        for name, val in [("new_admission",0),("re_admission",0),
                           ("tuition_receipt",0),("misc_receipt",0)]:
            c.execute("INSERT OR IGNORE INTO counters (name,value) VALUES (?,?)", (name,val))

        c.execute("""CREATE TABLE IF NOT EXISTS used_prefixes (
                prefix TEXT PRIMARY KEY,
                created_at TEXT DEFAULT (datetime('now','localtime')))""")

        c.execute("""CREATE TABLE IF NOT EXISTS receipt_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT (datetime('now','localtime')),
                receipt_no TEXT UNIQUE NOT NULL,
                student_name TEXT,
                parent_name TEXT,
                grade TEXT,
                section TEXT,
                reference_no TEXT,
                amount REAL,
                payment_mode TEXT,
                payment_date TEXT,
                fee_type TEXT,
                pdf_path TEXT,
                created_by TEXT DEFAULT 'system',
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now','localtime')))""")

        c.execute("""CREATE TABLE IF NOT EXISTS cancelled_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_receipt_no TEXT NOT NULL,
                student_name TEXT,
                amount REAL,
                fee_type TEXT,
                payment_mode TEXT,
                reason TEXT,
                cancelled_by TEXT,
                cancellation_pdf TEXT,
                cancelled_at TEXT DEFAULT (datetime('now','localtime')))""")

        c.execute("""CREATE TABLE IF NOT EXISTS misc_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT (datetime('now','localtime')),
                student_name TEXT,
                class TEXT,
                reference_no TEXT,
                payment_mode TEXT,
                amount REAL,
                fee_type TEXT DEFAULT 'MISC',
                receipt_no TEXT,
                status TEXT DEFAULT 'active')""")

        c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT (datetime('now','localtime')),
                username TEXT,
                role TEXT,
                action TEXT,
                details TEXT,
                ip_address TEXT)""")

        c.execute("""CREATE TABLE IF NOT EXISTS deleted_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT,
                reference_no TEXT,
                father_name TEXT,
                mother_name TEXT,
                deleted_reason TEXT DEFAULT 'TC',
                deleted_by TEXT,
                deleted_at TEXT DEFAULT (datetime('now','localtime')))""")

        c.execute("""CREATE TABLE IF NOT EXISTS daily_report_cache (
                report_date TEXT PRIMARY KEY,
                total_ra INTEGER DEFAULT 0,
                new_ra_today INTEGER DEFAULT 0,
                total_na INTEGER DEFAULT 0,
                new_na_today INTEGER DEFAULT 0,
                outstanding_yesterday REAL DEFAULT 0,
                collected_neft REAL DEFAULT 0,
                collected_cash REAL DEFAULT 0,
                tuition_collected REAL DEFAULT 0,
                misc_collected REAL DEFAULT 0,
                outstanding_after REAL DEFAULT 0,
                concession_today REAL DEFAULT 0,
                generated_by TEXT,
                generated_at TEXT DEFAULT (datetime('now','localtime')))""")

        conn.commit()
    finally:
        conn.close()
