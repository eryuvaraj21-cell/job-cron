"""
Database layer - SQLite tracking for applied jobs and job listings.
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "jobs.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT,
            platform TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            url TEXT UNIQUE NOT NULL,
            description TEXT,
            salary TEXT,
            posted_date TEXT,
            skills_required TEXT,
            match_score REAL DEFAULT 0,
            discovered_at TEXT NOT NULL,
            status TEXT DEFAULT 'discovered',
            applied_at TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS application_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        CREATE TABLE IF NOT EXISTS email_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            notification_type TEXT NOT NULL,
            subject TEXT,
            sent_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_platform ON jobs(platform);
    """)

    conn.commit()
    conn.close()


def job_exists(url: str) -> bool:
    """Check if a job URL already exists in DB."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM jobs WHERE url = ?", (url,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def save_job(job: dict) -> int:
    """Save a job listing. Returns the job ID."""
    conn = get_connection()
    cursor = conn.cursor()

    skills_str = ",".join(job.get("skills_required", []))

    cursor.execute("""
        INSERT OR IGNORE INTO jobs 
        (external_id, platform, title, company, location, url, description,
         salary, posted_date, skills_required, match_score, discovered_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job.get("external_id", ""),
        job["platform"],
        job["title"],
        job.get("company", ""),
        job.get("location", ""),
        job["url"],
        job.get("description", ""),
        job.get("salary", ""),
        job.get("posted_date", ""),
        skills_str,
        job.get("match_score", 0),
        datetime.now().isoformat(),
        "discovered",
    ))

    conn.commit()
    job_id = cursor.lastrowid
    conn.close()
    return job_id


def update_job_status(job_id: int, status: str, notes: str = ""):
    """Update job application status."""
    conn = get_connection()
    cursor = conn.cursor()

    applied_at = datetime.now().isoformat() if status == "applied" else None

    cursor.execute("""
        UPDATE jobs SET status = ?, notes = ?, applied_at = COALESCE(?, applied_at)
        WHERE id = ?
    """, (status, notes, applied_at, job_id))

    conn.commit()
    conn.close()


def log_application(job_id: int, action: str, status: str, message: str = ""):
    """Log an application action."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO application_log (job_id, action, status, message, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (job_id, action, status, message, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def get_jobs_by_status(status: str) -> list:
    """Get all jobs with a given status."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE status = ? ORDER BY discovered_at DESC", (status,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_unapplied_matched_jobs(min_score: float = 60) -> list:
    """Get matched jobs that haven't been applied to yet."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM jobs 
        WHERE status = 'matched' AND match_score >= ? 
        ORDER BY match_score DESC
    """, (min_score,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_today_stats() -> dict:
    """Get today's application statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT status, COUNT(*) as count FROM jobs 
        WHERE date(discovered_at) = ? GROUP BY status
    """, (today,))

    stats = {row["status"]: row["count"] for row in cursor.fetchall()}
    conn.close()
    return stats


def log_email_notification(job_id: int, notification_type: str, subject: str):
    """Log sent email notification."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO email_notifications (job_id, notification_type, subject, sent_at)
        VALUES (?, ?, ?, ?)
    """, (job_id, notification_type, subject, datetime.now().isoformat()))
    conn.commit()
    conn.close()
