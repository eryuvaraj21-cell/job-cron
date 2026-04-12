"""
Foundit.in (formerly Monster India) Job Scraper
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class FounditScraper(BaseRequestScraper):
    PLATFORM_NAME = "foundit"
    BASE_URL = "https://www.foundit.in"
    SEARCH_URL = "https://www.foundit.in/srp/results"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            params = {
                "query": title,
                "locations": location,
                "sort": "1",  # Sort by date
            }
            soup = self._get(f"{self.BASE_URL}/middleware/jobsearch", params=params)

            if not soup:
                # Fallback to URL-based search
                encoded = title.replace(" ", "-").lower()
                url = f"{self.BASE_URL}/search/{encoded}-jobs-in-{location.lower()}"
                soup = self._get(url)

            if not soup:
                return jobs

            cards = soup.select("div.card-apply-content, div.srpResultCardContainer, div.jobTuple")

            logger.info(f"[Foundit] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Foundit] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Foundit] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a.card-title, a.title, h3 a")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("span.company-name, a.company-name, span.comp-name")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span.location, span.loc, span.loc-text")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        exp_el = card.select_one("span.experience, span.exp")
        job["experience"] = exp_el.get_text(strip=True) if exp_el else ""

        return job
