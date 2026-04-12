"""
Adzuna Job Scraper (Aggregator)
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class AdzunaScraper(BaseRequestScraper):
    PLATFORM_NAME = "adzuna"
    BASE_URL = "https://www.adzuna.in"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            encoded = title.replace(" ", "+")
            url = f"{self.BASE_URL}/search?q={encoded}&loc={quote_plus(location)}&sb=date"

            soup = self._get(url)
            if not soup:
                return jobs

            cards = soup.select("div.ui-search-results div[data-aid], div[class*='ResultCard']")

            logger.info(f"[Adzuna] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Adzuna] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Adzuna] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a[class*='title'], h2 a")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("div[class*='company'], span.company")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span[class*='location'], div.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        return job
