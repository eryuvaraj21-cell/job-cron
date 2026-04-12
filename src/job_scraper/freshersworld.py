"""
Freshersworld Job Scraper (has experienced jobs too)
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class FreshersworldScraper(BaseRequestScraper):
    PLATFORM_NAME = "freshersworld"
    BASE_URL = "https://www.freshersworld.com"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            encoded = title.replace(" ", "+")
            url = f"{self.BASE_URL}/jobs/search"
            params = {"search": title, "location": location, "experience": "3-6"}

            soup = self._get(url, params=params)
            if not soup:
                return jobs

            cards = soup.select("div.job-container, div.job-details, div[class*='jobDetail']")

            logger.info(f"[Freshersworld] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Freshersworld] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Freshersworld] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a.job-title, h3 a, a[class*='title']")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("span.company-name, div.company")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span.location, div.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        return job
