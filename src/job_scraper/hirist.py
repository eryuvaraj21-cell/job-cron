"""
Hirist.tech Job Scraper (Tech-focused India job board)
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class HiristScraper(BaseRequestScraper):
    PLATFORM_NAME = "hirist"
    BASE_URL = "https://www.hirist.tech"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            encoded = title.replace(" ", "-").lower()
            loc = location.lower()
            url = f"{self.BASE_URL}/{encoded}-jobs-in-{loc}?experience=3-6"

            soup = self._get(url)
            if not soup:
                return jobs

            cards = soup.select("div.job-card, div.jobCard, div[class*='vacancy']")

            logger.info(f"[Hirist] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Hirist] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Hirist] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a.job-title, a[class*='title'], h3 a")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("span.company, div.company-name")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span.location, div.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        return job
