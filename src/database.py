"""
Database layer - SQLite tracking for applied jobs and job listings.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "jobs.db"


@contextmanager
def _get_conn():
    """Context-managed connection; auto-commits and closes."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# Keep get_connection for any callers outside this module.
def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize database tables."""
    with _get_conn() as conn:
        conn.executescript("""
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


def job_exists(url: str) -> bool:
    """Check if a job URL already exists in DB."""
    with _get_conn() as conn:
        row = conn.execute("SELECT 1 FROM jobs WHERE url = ?", (url,)).fetchone()
        return row is not None


def filter_new_urls(urls: list) -> set:
    """Return the subset of *urls* not yet in the DB (batch check)."""
    if not urls:
        return set()
    placeholders = ",".join("?" * len(urls))
    with _get_conn() as conn:
        rows = conn.execute(
            f"SELECT url FROM jobs WHERE url IN ({placeholders})", urls
        ).fetchall()
    existing = {row["url"] for row in rows}
    return set(urls) - existing


def save_job(job: dict) -> int:
    """Save a job listing. Returns the job ID."""
    skills_str = ",".join(job.get("skills_required", []))
    with _get_conn() as conn:
        conn.execute("""
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
        return conn.execute("SELECT id FROM jobs WHERE url = ?", (job["url"],)).fetchone()["id"]


def update_job_status(job_id: int, status: str, notes: str = ""):
    """Update job application status."""
    applied_at = datetime.now().isoformat() if status == "applied" else None
    with _get_conn() as conn:
        conn.execute("""
            UPDATE jobs SET status = ?, notes = ?, applied_at = COALESCE(?, applied_at)
            WHERE id = ?
        """, (status, notes, applied_at, job_id))


def log_application(job_id: int, action: str, status: str, message: str = ""):
    """Log an application action."""
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO application_log (job_id, action, status, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (job_id, action, status, message, datetime.now().isoformat()))


def get_jobs_by_status(status: str) -> list:
    """Get all jobs with a given status."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY discovered_at DESC", (status,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_unapplied_matched_jobs(min_score: float = 60) -> list:
    """Get matched jobs that haven't been applied to yet."""
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM jobs 
            WHERE status = 'matched' AND match_score >= ? 
            ORDER BY match_score DESC
        """, (min_score,)).fetchall()
    return [dict(row) for row in rows]


def get_today_stats() -> dict:
    """Get today's application statistics."""
    today = datetime.now().strftime("%Y-%m-%d")
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT status, COUNT(*) as count FROM jobs 
            WHERE date(discovered_at) = ? GROUP BY status
        """, (today,)).fetchall()
    return {row["status"]: row["count"] for row in rows}


def log_email_notification(job_id: int, notification_type: str, subject: str):
    """Log sent email notification."""
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO email_notifications (job_id, notification_type, subject, sent_at)
            VALUES (?, ?, ?, ?)
        """, (job_id, notification_type, subject, datetime.now().isoformat()))
