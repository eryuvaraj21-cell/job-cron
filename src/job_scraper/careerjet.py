"""
CareerJet Job Scraper (Aggregator)
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class CareerJetScraper(BaseRequestScraper):
    PLATFORM_NAME = "careerjet"
    BASE_URL = "https://www.careerjet.co.in"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            url = f"{self.BASE_URL}/search/jobs"
            params = {"s": title, "l": location, "sort": "date", "radius": 50}

            soup = self._get(url, params=params)
            if not soup:
                return jobs

            cards = soup.select("article.job, div.job, section.job")

            logger.info(f"[CareerJet] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[CareerJet] Parse error: {e}")
        except Exception as e:
            logger.error(f"[CareerJet] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("a.job-title, header a, h2 a")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        job["url"] = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        company_el = card.select_one("p.company, span.company")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("ul.location li, span.location")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        return job
