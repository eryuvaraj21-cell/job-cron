"""
TimesJobs Scraper
"""

import logging
from urllib.parse import quote_plus

from .base_request import BaseRequestScraper

logger = logging.getLogger(__name__)


class TimesJobsScraper(BaseRequestScraper):
    PLATFORM_NAME = "timesjobs"
    BASE_URL = "https://www.timesjobs.com"

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            url = (
                f"{self.BASE_URL}/candidate/job-search.html"
                f"?searchType=personal498"
                f"&from=submit"
                f"&txtKeywords={quote_plus(title)}"
                f"&txtLocation={quote_plus(location)}"
                f"&cboWorkExp1=4"
                f"&cboWorkExp2=6"
            )
            soup = self._get(url)
            if not soup:
                return jobs

            cards = soup.select("li.clearfix.job-bx.wht-shd-bx")

            logger.info(f"[TimesJobs] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[TimesJobs] Parse error: {e}")
        except Exception as e:
            logger.error(f"[TimesJobs] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}

        title_el = card.select_one("h2 a")
        if not title_el:
            return None
        job["title"] = title_el.get_text(strip=True)
        job["url"] = title_el.get("href", "")

        company_el = card.select_one("h3.joblist-comp-name, h3 a")
        job["company"] = company_el.get_text(strip=True) if company_el else ""

        loc_el = card.select_one("span.location-text, ul.top-jd-dtl li span")
        job["location"] = loc_el.get_text(strip=True) if loc_el else ""

        # Skills
        skill_els = card.select("span.srp-skills, a.skils")
        job["skills_required"] = [s.get_text(strip=True) for s in skill_els]

        return job
