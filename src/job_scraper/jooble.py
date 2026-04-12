"""
Jooble Job Scraper (Aggregator)
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class JoobleScraper(BaseRequestScraper):
    PLATFORM_NAME = "jooble"
    BASE_URL = "https://in.jooble.org"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            url = f"{self.BASE_URL}/SearchResult"
            params = {"ukw": title, "uloc": location, "date": "3"}

            soup = self._get(url, params=params)
            if not soup:
                return jobs

            cards = soup.select("article[class*='vacancy'], div[data-test-name='vacancy']")

            logger.info(f"[Jooble] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Jooble] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Jooble] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a[class*='link'], h2 a, a[data-test-name='link']")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("p[class*='company'], span.company-name")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span[class*='location'], div.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        return job
