"""
Dice.com Job Scraper (Tech-focused)
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class DiceScraper(BaseRequestScraper):
    PLATFORM_NAME = "dice"
    BASE_URL = "https://www.dice.com"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            url = f"{self.BASE_URL}/jobs"
            params = {"q": title, "location": location, "countryCode": "IN", "radius": "50", "postedDate": "SEVEN"}

            soup = self._get(url, params=params)
            if not soup:
                return jobs

            cards = soup.select("dhi-search-card, div.card-job, div[class*='search-card']")

            logger.info(f"[Dice] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Dice] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Dice] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a.card-title-link, a[data-cy='card-title-link'], h5 a")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("span[data-cy='search-result-company-name'], a.company-name")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span[data-cy='search-result-location'], span.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        return job
