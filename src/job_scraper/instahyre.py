"""
Instahyre Job Scraper
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class InstahyreScraper(BaseRequestScraper):
    PLATFORM_NAME = "instahyre"
    BASE_URL = "https://www.instahyre.com"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            # Instahyre has a JSON API
            params = {
                "job_title": title,
                "location": location,
                "experience_min": 3,
                "experience_max": 6,
            }
            url = f"{self.BASE_URL}/search-jobs/"
            soup = self._get(url, params=params)
            if not soup:
                return jobs

            cards = soup.select("div.job-card, div.opportunity-card, div[class*='job']")

            logger.info(f"[Instahyre] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Instahyre] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Instahyre] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a[class*='title'], h3 a, div.job-title a")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("div.company-name, span.company")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span.location, div.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        return job
