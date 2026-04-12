"""
Talent.com Job Scraper (Aggregator)
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class TalentScraper(BaseRequestScraper):
    PLATFORM_NAME = "talent"
    BASE_URL = "https://in.talent.com"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            url = f"{self.BASE_URL}/jobs"
            params = {"k": title, "l": location, "datePosted": "3days"}

            soup = self._get(url, params=params)
            if not soup:
                return jobs

            cards = soup.select("div.card--job, div[class*='card-job'], div.link-job-wrap")

            logger.info(f"[Talent.com] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Talent.com] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Talent.com] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a.link-job-wrap, h2 a, a[class*='card__job']")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("span.card__job-empname-text, div.company")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span.card__job-location, div.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        return job
