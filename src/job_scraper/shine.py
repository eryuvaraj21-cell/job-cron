"""
Shine.com Job Scraper
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class ShineScraper(BaseRequestScraper):
    PLATFORM_NAME = "shine"
    BASE_URL = "https://www.shine.com"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            encoded = title.replace(" ", "-").lower()
            loc = location.lower()
            url = f"{self.BASE_URL}/job-search/{encoded}-jobs-in-{loc}"

            soup = self._get(url)
            if not soup:
                return jobs

            cards = soup.select("div.job_container, div.jobCard, div[id^='job_']")

            logger.info(f"[Shine] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Shine] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Shine] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a.job_title, a.jobTitle, h3 a")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("span.company_name, a.company_name, span.companyName")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span.location, span.loc")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        exp_el = card.select_one("span.experience, span.exp")
        job["experience"] = exp_el.get_text(strip=True) if exp_el else ""

        return job
