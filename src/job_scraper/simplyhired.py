"""
SimplyHired Job Scraper
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class SimplyHiredScraper(BaseRequestScraper):
    PLATFORM_NAME = "simplyhired"
    BASE_URL = "https://www.simplyhired.co.in"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            url = f"{self.BASE_URL}/search"
            params = {"q": title, "l": location, "sb": "dd"}  # Sort by date
            soup = self._get(url, params=params)
            if not soup:
                return jobs

            cards = soup.select("article.SerpJob, div.SerpJob, li.SerpJob")

            logger.info(f"[SimplyHired] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[SimplyHired] Parse error: {e}")
        except Exception as e:
            logger.error(f"[SimplyHired] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a[data-mdref], h2 a, a.SerpJob-link")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("span.JobPosting-labelWithIcon, span.company-name")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span.JobPosting-labelWithIcon.location, span.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        return job
