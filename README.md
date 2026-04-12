# 🤖 Job Auto-Apply Bot

Automated job application bot that parses your resume, scrapes jobs from **LinkedIn**, **Naukri**, and **Indeed**, matches them to your skills, and auto-applies every 30 minutes. Sends you email alerts when manual action is needed.

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                  Every 30 Minutes                       │
├─────────────────────────────────────────────────────────┤
│  1. Parse Resume  →  Extract skills, experience         │
│  2. Scrape Jobs   →  LinkedIn, Naukri, Indeed           │
│  3. Match & Score →  Compare job requirements vs skills │
│  4. Auto-Apply    →  Submit applications automatically  │
│  5. Notify        →  Email you when manual action needed│
└─────────────────────────────────────────────────────────┘
```

## Features

- **Resume Parsing** - Extracts skills, experience, education from PDF/DOCX
- **Multi-Platform** - LinkedIn (Easy Apply), Naukri, Indeed
- **Smart Matching** - Scores jobs based on skill overlap, title relevance, and experience fit
- **Auto-Apply** - Submits applications via browser automation
- **Email Alerts** - Notifies you when a job needs manual login, extra info, or portal access
- **Duplicate Prevention** - SQLite database tracks all jobs to avoid re-applying
- **Daily Summary** - Sends a daily stats email
- **Docker Ready** - Run it as a container

---

## Quick Start

### 1. Clone & Install

```bash
cd job-cron
pip install -r requirements.txt
```

### 2. Add Your Resume

Place your resume (PDF or DOCX) in the `resume/` folder:

```bash
mkdir resume
cp /path/to/your/resume.pdf resume/resume.pdf
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:

```env
# Your details
YOUR_NAME=John Doe
YOUR_EMAIL=john@example.com

# LinkedIn credentials
LINKEDIN_EMAIL=john@example.com
LINKEDIN_PASSWORD=your-password

# Naukri credentials
NAUKRI_EMAIL=john@example.com
NAUKRI_PASSWORD=your-password

# Email notifications (Gmail App Password)
SMTP_EMAIL=john@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx    # Gmail App Password
NOTIFY_EMAIL=john@gmail.com

# Resume location
RESUME_PATH=resume/resume.pdf
```

> **Gmail App Password**: Go to Google Account → Security → 2-Step Verification → App Passwords → Generate one for "Mail".

### 4. Customize Job Search

Edit `config/config.yaml`:

```yaml
search:
  titles:
    - Software Engineer
    - Python Developer
    - Full Stack Developer
  locations:
    - Bangalore
    - Remote
  experience_years: 3

matching:
  min_score: 60        # Only apply if match score >= 60%
  min_skills_match: 3  # At least 3 skills should match
```

### 5. Run

```bash
python -m src.main
```

The bot will:
- Run immediately on startup
- Then repeat every 30 minutes
- Send you email when jobs need manual attention

---

## Run with Docker

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

---

## Project Structure

```
job-cron/
├── config/
│   └── config.yaml          # Job search settings, filters, thresholds
├── resume/
│   └── resume.pdf           # Your resume (PDF/DOCX)
├── src/
│   ├── main.py              # Entry point & 30-min scheduler
│   ├── resume_parser.py     # Resume → skills/experience extraction
│   ├── job_matcher.py       # Scores jobs against your profile
│   ├── email_notifier.py    # Email alerts & daily summary
│   ├── database.py          # SQLite job tracking
│   └── job_scraper/
│       ├── base.py          # Base Selenium scraper
│       ├── linkedin.py      # LinkedIn Easy Apply
│       ├── naukri.py        # Naukri auto-apply
│       └── indeed.py        # Indeed auto-apply
├── data/
│   └── jobs.db              # Auto-created SQLite database
├── logs/                    # Daily log files
├── .env                     # Your credentials (gitignored)
├── .env.example             # Template
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Email Notifications

You'll receive emails for:

| Scenario | Email |
|----------|-------|
| Job needs portal login | 🔐 "Login required for [Platform]" |
| Job needs extra details | 🔔 "X job(s) need your attention" with direct links |
| Successful auto-apply | ✅ "Applied to X job(s) automatically" |
| Daily summary | 📊 Stats: applied, skipped, manual needed |

---

## Configuration Reference

### `.env` Variables

| Variable | Description |
|----------|-------------|
| `LINKEDIN_EMAIL` / `PASSWORD` | LinkedIn credentials |
| `NAUKRI_EMAIL` / `PASSWORD` | Naukri credentials |
| `SMTP_EMAIL` / `PASSWORD` | Gmail for sending notifications |
| `NOTIFY_EMAIL` | Where to receive alerts |
| `RESUME_PATH` | Path to resume file |
| `CRON_INTERVAL_MINUTES` | How often to run (default: 30) |
| `BROWSER_HEADLESS` | `true` for headless, `false` to see browser |

### `config.yaml` Settings

| Setting | Description |
|---------|-------------|
| `search.titles` | Job titles to search for |
| `search.locations` | Locations to search in |
| `matching.min_score` | Minimum match score (0-100) to auto-apply |
| `platforms.*.enabled` | Enable/disable each platform |
| `platforms.*.max_applications_per_run` | Limit applications per cycle |
| `filters.exclude_companies` | Companies to skip |
| `filters.exclude_titles` | Title keywords to skip (e.g., "intern") |

---

## Troubleshooting

**Bot can't login to LinkedIn/Naukri**
- Check credentials in `.env`
- Set `BROWSER_HEADLESS=false` to watch what happens
- LinkedIn may require CAPTCHA - you'll get an email about it

**No jobs being found**
- Check job titles and locations in `config.yaml`
- Make sure the platform is enabled
- Check `logs/` for detailed error messages

**Chrome issues**
- Install Chrome: `apt install google-chrome-stable` (Linux) or download from google.com
- The bot auto-downloads ChromeDriver via `webdriver-manager`

---

## ⚠️ Important Notes

1. **Rate Limiting**: The bot has built-in delays to avoid being flagged. Don't reduce them.
2. **LinkedIn**: Uses Easy Apply only by default. External applications trigger email notifications.
3. **Naukri**: Some jobs redirect to company portals - you'll be notified via email.
4. **Terms of Service**: Automated applications may violate platform ToS. Use at your own risk.
5. **Credentials**: Never commit your `.env` file. It's gitignored by default.
