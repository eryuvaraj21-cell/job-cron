"""
Jobrapido Job Scraper (Aggregator)
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class JobrapidoScraper(BaseRequestScraper):
    PLATFORM_NAME = "jobrapido"
    BASE_URL = "https://in.jobrapido.com"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            url = f"{self.BASE_URL}/jobsearch"
            params = {"w": title, "l": location, "r": "auto"}

            soup = self._get(url, params=params)
            if not soup:
                return jobs

            cards = soup.select("article.result, div.result-item, div[class*='result']")

            logger.info(f"[Jobrapido] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Jobrapido] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Jobrapido] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a.result__title, h2 a, a[class*='title']")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("span.result__company, span.company")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span.result__location, span.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        return job
