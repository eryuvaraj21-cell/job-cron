"""
CutShort Job Scraper (Tech startup focused)
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class CutShortScraper(BaseRequestScraper):
    PLATFORM_NAME = "cutshort"
    BASE_URL = "https://cutshort.io"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            url = f"{self.BASE_URL}/jobs"
            params = {"q": title, "location": location, "experience": "3-6"}

            soup = self._get(url, params=params)
            if not soup:
                return jobs

            cards = soup.select("div[class*='job-card'], div[class*='JobCard'], a[class*='job-listing']")

            logger.info(f"[CutShort] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[CutShort] Parse error: {e}")
        except Exception as e:
            logger.error(f"[CutShort] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a[class*='title'], h3 a, div.job-title")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("div.company-name, span.company, a[class*='company']")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span.location, div.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        skill_els = card.select("span.skill-tag, span[class*='skill'], span.chip")
        job["skills_required"] = [s.get_text(strip=True) for s in skill_els]

        return job
