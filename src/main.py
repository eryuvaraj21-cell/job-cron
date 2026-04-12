"""
Main Entry Point - Job Auto-Apply Bot with 30-minute scheduling.
"""

import os
import sys
import logging
import signal
from pathlib import Path
from datetime import datetime

import yaml
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.resume_parser import ResumeParser
from src.job_matcher import JobMatcher
from src.job_scraper.linkedin import LinkedInScraper
from src.job_scraper.naukri import NaukriScraper
from src.job_scraper.glassdoor import GlassdoorScraper
from src.job_scraper.foundit import FounditScraper
from src.job_scraper.timesjobs import TimesJobsScraper
from src.job_scraper.shine import ShineScraper
from src.job_scraper.instahyre import InstahyreScraper
from src.job_scraper.wellfound import WellfoundScraper
from src.job_scraper.simplyhired import SimplyHiredScraper
from src.job_scraper.hirist import HiristScraper
from src.job_scraper.cutshort import CutShortScraper
from src.job_scraper.google_jobs import GoogleJobsScraper
from src.job_scraper.jooble import JoobleScraper
from src.job_scraper.adzuna import AdzunaScraper
from src.job_scraper.careerjet import CareerJetScraper
from src.job_scraper.talent import TalentScraper
from src.job_scraper.dice import DiceScraper
from src.job_scraper.freshersworld import FreshersworldScraper
from src.job_scraper.jobrapido import JobrapidoScraper
from src.email_notifier import EmailNotifier
from src import database as db

# ─── Load configuration ────────────────────────────────────────────

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)


# ─── Logging setup ─────────────────────────────────────────────────

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("job-bot")


# ─── Initialize components ─────────────────────────────────────────

def get_notifier() -> EmailNotifier:
    return EmailNotifier(
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_email=os.getenv("SMTP_EMAIL", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        notify_email=os.getenv("NOTIFY_EMAIL", ""),
    )


def get_resume_profile():
    resume_path = os.getenv("RESUME_PATH", "resume/resume.pdf")
    full_path = PROJECT_ROOT / resume_path

    if not full_path.exists():
        logger.error(f"Resume not found at: {full_path}")
        logger.error("Place your resume in the 'resume/' folder and update RESUME_PATH in .env")
        return None

    parser = ResumeParser(str(full_path))
    profile = parser.parse()

    logger.info(f"Resume parsed: {profile.name}")
    logger.info(f"Skills found: {', '.join(profile.skills[:15])}...")
    logger.info(f"Experience: {profile.experience_years} years")

    return profile


# ─── Core job processing pipeline ──────────────────────────────────

def process_platform(scraper, platform_config, email, password, profile, matcher, resume_path, notifier):
    """Run the full pipeline for one platform."""
    platform_name = scraper.PLATFORM_NAME
    manual_needed_jobs = []
    applied_jobs = []

    if not platform_config.get("enabled", False):
        logger.info(f"[{platform_name}] Platform disabled, skipping")
        return applied_jobs, manual_needed_jobs

    max_applications = platform_config.get("max_applications_per_run", 10)
    applied_count = 0

    try:
        # Login
        if not scraper.login(email, password):
            logger.warning(f"[{platform_name}] Login failed")
            notifier.notify_login_required(platform_name, "Login failed - check credentials")
            return applied_jobs, manual_needed_jobs

        # Search for jobs using configured titles and locations
        all_jobs = []
        search_titles = CONFIG.get("search", {}).get("titles", [])
        search_locations = CONFIG.get("search", {}).get("locations", [])

        for title in search_titles:
            for location in search_locations:
                if applied_count >= max_applications:
                    break

                logger.info(f"[{platform_name}] Searching: '{title}' in '{location}'")
                jobs = scraper.search_jobs(title, location)
                all_jobs.extend(jobs)

        logger.info(f"[{platform_name}] Total jobs found: {len(all_jobs)}")

        # Process each job
        for job in all_jobs:
            if applied_count >= max_applications:
                logger.info(f"[{platform_name}] Reached max applications per run ({max_applications})")
                break

            job_url = job.get("url", "")

            # Skip if already in database
            if db.job_exists(job_url):
                continue

            # Score and match
            should_apply, score, reason = matcher.should_apply(job)
            job["match_score"] = score

            # Save to database
            job_id = db.save_job(job)

            if not should_apply:
                logger.info(f"[{platform_name}] Skipping (score {score:.0f}): {job.get('title', '')} @ {job.get('company', '')}")
                db.update_job_status(job_id, "skipped", reason)
                continue

            # Update status to matched
            db.update_job_status(job_id, "matched", reason)
            logger.info(f"[{platform_name}] Match (score {score:.0f}): {job.get('title', '')} @ {job.get('company', '')}")

            # Try to apply
            result = scraper.apply_to_job(job, str(PROJECT_ROOT / resume_path))

            if result["status"] == "applied":
                db.update_job_status(job_id, "applied", result["message"])
                db.log_application(job_id, "auto_apply", "success", result["message"])
                applied_jobs.append(job)
                applied_count += 1
                logger.info(f"[{platform_name}] APPLIED: {job.get('title', '')} @ {job.get('company', '')}")

            elif result["status"] == "manual_needed":
                db.update_job_status(job_id, "manual_needed", result["message"])
                db.log_application(job_id, "auto_apply", "manual_needed", result["message"])
                job["message"] = result["message"]
                manual_needed_jobs.append(job)
                logger.info(f"[{platform_name}] MANUAL NEEDED: {job.get('title', '')} - {result['message']}")

            elif result["status"] == "already_applied":
                db.update_job_status(job_id, "applied", "Already applied")
                logger.info(f"[{platform_name}] Already applied: {job.get('title', '')}")

            else:
                db.update_job_status(job_id, "failed", result["message"])
                db.log_application(job_id, "auto_apply", "failed", result["message"])
                logger.warning(f"[{platform_name}] FAILED: {job.get('title', '')} - {result['message']}")

    except Exception as e:
        logger.error(f"[{platform_name}] Pipeline error: {e}", exc_info=True)
    finally:
        scraper.stop()

    return applied_jobs, manual_needed_jobs


# ─── Main cron job ──────────────────────────────────────────────────

def run_job_cycle():
    """Execute one full cycle: scrape → match → apply → notify."""
    logger.info("=" * 60)
    logger.info(f"Starting job cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # Parse resume
    profile = get_resume_profile()
    if not profile:
        return

    matcher = JobMatcher(profile, CONFIG)
    notifier = get_notifier()
    resume_path = os.getenv("RESUME_PATH", "resume/resume.pdf")
    headless = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
    chrome_binary = os.getenv("CHROME_BINARY_PATH", "")

    all_applied = []
    all_manual_needed = []

    platform_configs = CONFIG.get("platforms", {})

    # ── LinkedIn ──
    if platform_configs.get("linkedin", {}).get("enabled", False):
        scraper = LinkedInScraper(headless=headless, chrome_binary=chrome_binary)
        applied, manual = process_platform(
            scraper,
            platform_configs["linkedin"],
            os.getenv("LINKEDIN_EMAIL", ""),
            os.getenv("LINKEDIN_PASSWORD", ""),
            profile, matcher, resume_path, notifier,
        )
        all_applied.extend(applied)
        all_manual_needed.extend(manual)

    # ── Naukri ──
    if platform_configs.get("naukri", {}).get("enabled", False):
        scraper = NaukriScraper(headless=headless, chrome_binary=chrome_binary)
        applied, manual = process_platform(
            scraper,
            platform_configs["naukri"],
            os.getenv("NAUKRI_EMAIL", ""),
            os.getenv("NAUKRI_PASSWORD", ""),
            profile, matcher, resume_path, notifier,
        )
        all_applied.extend(applied)
        all_manual_needed.extend(manual)

    # ── Glassdoor ──
    if platform_configs.get("glassdoor", {}).get("enabled", False):
        scraper = GlassdoorScraper(headless=headless, chrome_binary=chrome_binary)
        applied, manual = process_platform(
            scraper, platform_configs["glassdoor"], "", "",
            profile, matcher, resume_path, notifier,
        )
        all_applied.extend(applied)
        all_manual_needed.extend(manual)

    # ── Wellfound (AngelList) ──
    if platform_configs.get("wellfound", {}).get("enabled", False):
        scraper = WellfoundScraper(headless=headless, chrome_binary=chrome_binary)
        applied, manual = process_platform(
            scraper, platform_configs["wellfound"], "", "",
            profile, matcher, resume_path, notifier,
        )
        all_applied.extend(applied)
        all_manual_needed.extend(manual)

    # ── Google Jobs ──
    if platform_configs.get("google_jobs", {}).get("enabled", False):
        scraper = GoogleJobsScraper(headless=headless, chrome_binary=chrome_binary)
        applied, manual = process_platform(
            scraper, platform_configs["google_jobs"], "", "",
            profile, matcher, resume_path, notifier,
        )
        all_applied.extend(applied)
        all_manual_needed.extend(manual)

    # ── Request-based scrapers (no browser needed, faster) ──
    request_scrapers = {
        "foundit": FounditScraper,
        "timesjobs": TimesJobsScraper,
        "shine": ShineScraper,
        "instahyre": InstahyreScraper,
        "simplyhired": SimplyHiredScraper,
        "hirist": HiristScraper,
        "cutshort": CutShortScraper,
        "jooble": JoobleScraper,
        "adzuna": AdzunaScraper,
        "careerjet": CareerJetScraper,
        "talent": TalentScraper,
        "dice": DiceScraper,
        "freshersworld": FreshersworldScraper,
        "jobrapido": JobrapidoScraper,
    }

    for name, ScraperClass in request_scrapers.items():
        if platform_configs.get(name, {}).get("enabled", False):
            try:
                scraper = ScraperClass()
                applied, manual = process_platform(
                    scraper, platform_configs[name], "", "",
                    profile, matcher, resume_path, notifier,
                )
                all_applied.extend(applied)
                all_manual_needed.extend(manual)
            except Exception as e:
                logger.error(f"[{name}] Scraper failed: {e}")

    # ── Send notifications ──
    notify_config = CONFIG.get("notifications", {})

    if all_manual_needed and notify_config.get("on_manual_action_needed", True):
        notifier.notify_manual_action_needed(all_manual_needed)

    if all_applied and notify_config.get("on_successful_apply", True):
        notifier.notify_successful_applications(all_applied)

    # ── Summary ──
    logger.info("-" * 60)
    logger.info(f"Cycle complete: {len(all_applied)} applied, {len(all_manual_needed)} need attention")
    logger.info("-" * 60)


def send_daily_summary():
    """Send daily stats email."""
    notifier = get_notifier()
    stats = db.get_today_stats()
    notifier.send_daily_summary(stats)
    logger.info("Daily summary email sent")


# ─── Scheduler ──────────────────────────────────────────────────────

def main():
    """Start the bot with APScheduler."""
    logger.info("Job Auto-Apply Bot starting...")

    # Initialize database
    db.init_db()
    logger.info("Database initialized")

    # Validate resume exists
    resume_path = os.getenv("RESUME_PATH", "resume/resume.pdf")
    full_resume_path = PROJECT_ROOT / resume_path
    if not full_resume_path.exists():
        logger.error(f"Resume not found: {full_resume_path}")
        logger.error("Please place your resume (PDF/DOCX) in the 'resume/' folder")
        logger.error("Then set RESUME_PATH in .env (e.g., RESUME_PATH=resume/resume.pdf)")
        sys.exit(1)

    interval = int(os.getenv("CRON_INTERVAL_MINUTES", "30"))

    scheduler = BlockingScheduler()

    # Main job cycle - every 30 minutes
    scheduler.add_job(
        run_job_cycle,
        trigger=IntervalTrigger(minutes=interval),
        id="job_cycle",
        name=f"Job scrape & apply (every {interval} min)",
        next_run_time=datetime.now(),  # Run immediately on start
        max_instances=1,
        misfire_grace_time=300,
    )

    # Daily summary - configurable time
    summary_time = CONFIG.get("notifications", {}).get("daily_summary_time", "20:00")
    if CONFIG.get("notifications", {}).get("daily_summary", True):
        hour, minute = summary_time.split(":")
        scheduler.add_job(
            send_daily_summary,
            trigger=CronTrigger(hour=int(hour), minute=int(minute)),
            id="daily_summary",
            name=f"Daily summary email at {summary_time}",
        )

    # Graceful shutdown
    def shutdown(signum, frame):
        logger.info("Shutting down...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info(f"Scheduler started: running every {interval} minutes")
    logger.info(f"Notifications will be sent to: {os.getenv('NOTIFY_EMAIL', 'not configured')}")
    logger.info("Press Ctrl+C to stop")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")


if __name__ == "__main__":
    main()
