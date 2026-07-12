"""
Job-Bot Mobile Dashboard — FastAPI backend.

Start standalone:  uvicorn src.dashboard:app --host 0.0.0.0 --port 8080 --reload
Or via main.py which spawns it in a background thread automatically.
"""

import asyncio
import json
import logging
import os
import sys
import threading
from collections import deque
from datetime import datetime, date
from pathlib import Path
from typing import Generator

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent))
from src import database as db

logger = logging.getLogger(__name__)

# ── Shared state ──────────────────────────────────────────────────────────────

class BotState:
    def __init__(self):
        self.running = False
        self.last_run: str | None = None
        self.last_run_result: str = "never"
        self.log_buffer: deque = deque(maxlen=200)
        self._lock = threading.Lock()
        self._run_fn = None            # set by main.py to run_job_cycle

    def set_run_fn(self, fn):
        self._run_fn = fn

    def add_log(self, line: str):
        with self._lock:
            self.log_buffer.append({"ts": datetime.now().isoformat(), "msg": line})

    def get_logs(self):
        with self._lock:
            return list(self.log_buffer)


bot_state = BotState()


# ── Log handler that feeds the in-memory buffer ───────────────────────────────

class BufferHandler(logging.Handler):
    def emit(self, record):
        try:
            bot_state.add_log(self.format(record))
        except Exception:
            pass


_buf_handler = BufferHandler()
_buf_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))
logging.getLogger().addHandler(_buf_handler)


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="Job-Bot Dashboard", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard loading…</h1>")


@app.get("/api/status")
def get_status():
    return {
        "running": bot_state.running,
        "last_run": bot_state.last_run,
        "last_run_result": bot_state.last_run_result,
    }


@app.post("/api/run")
def trigger_run(background_tasks: BackgroundTasks):
    if bot_state.running:
        return JSONResponse({"ok": False, "message": "Cycle already in progress"}, status_code=409)
    if bot_state._run_fn is None:
        return JSONResponse({"ok": False, "message": "Bot not initialised"}, status_code=503)

    def _run():
        bot_state.running = True
        bot_state.last_run = datetime.now().isoformat()
        try:
            bot_state._run_fn()
            bot_state.last_run_result = "success"
        except Exception as exc:
            bot_state.last_run_result = f"error: {exc}"
            logger.error(f"[dashboard] Manual cycle error: {exc}", exc_info=True)
        finally:
            bot_state.running = False

    background_tasks.add_task(_run)
    return {"ok": True, "message": "Cycle started"}


@app.get("/api/stats")
def get_stats():
    today = date.today().isoformat()
    try:
        today_stats = db.get_today_stats()
    except Exception:
        today_stats = {}

    try:
        import sqlite3
        conn = db.get_connection()
        rows = conn.execute("""
            SELECT
                COUNT(*) total,
                SUM(CASE WHEN status='applied' THEN 1 ELSE 0 END) applied,
                SUM(CASE WHEN status='manual_needed' THEN 1 ELSE 0 END) manual_needed,
                SUM(CASE WHEN status='skipped' THEN 1 ELSE 0 END) skipped,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) failed
            FROM jobs
        """).fetchone()
        conn.close()
        all_time = dict(rows) if rows else {}
    except Exception:
        all_time = {}

    return {"today": today_stats, "all_time": all_time, "date": today}


@app.get("/api/jobs")
def get_jobs(limit: int = 50, status: str = ""):
    try:
        conn = db.get_connection()
        if status:
            rows = conn.execute(
                "SELECT id,platform,title,company,location,url,match_score,status,discovered_at,applied_at "
                "FROM jobs WHERE status=? ORDER BY discovered_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,platform,title,company,location,url,match_score,status,discovered_at,applied_at "
                "FROM jobs ORDER BY discovered_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/logs")
def get_logs(last: int = 100):
    logs = bot_state.get_logs()
    return logs[-last:]


@app.get("/api/logs/stream")
def stream_logs():
    """Server-Sent Events endpoint for live log streaming."""
    seen = len(bot_state.get_logs())

    def event_gen() -> Generator:
        nonlocal seen
        import time
        while True:
            logs = bot_state.get_logs()
            if len(logs) > seen:
                for entry in logs[seen:]:
                    payload = json.dumps(entry)
                    yield f"data: {payload}\n\n"
                seen = len(logs)
            time.sleep(0.5)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


def start_dashboard(host: str = "0.0.0.0", port: int = 8080):
    """Launch uvicorn in a daemon thread; call from main.py."""
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    def _serve():
        asyncio.run(server.serve())

    t = threading.Thread(target=_serve, daemon=True, name="dashboard")
    t.start()
    logger.info(f"[dashboard] Mobile dashboard running at http://{host}:{port}")
    return t
