"""Single-cycle runner for GitHub Actions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import run_job_cycle
from src import database as db

db.init_db()
run_job_cycle()
