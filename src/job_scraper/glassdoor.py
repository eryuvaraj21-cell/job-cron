"""
Glassdoor Job Scraper
"""

import logging
import time
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from .base import BaseScraper

logger = logging.getLogger(__name__)


class GlassdoorScraper(BaseScraper):
    PLATFORM_NAME = "glassdoor"
    BASE_URL = "https://www.glassdoor.co.in"

    def login(self, email: str, password: str) -> bool:
        """Glassdoor search works without login."""
        self.start()
        logger.info("[Glassdoor] Browser started (no login needed)")
        return True

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            encoded_title = quote_plus(title)
            encoded_location = quote_plus(location)
            url = f"{self.BASE_URL}/Job/jobs.htm?sc.keyword={encoded_title}&locT=C&locKeyword={encoded_location}"

            self._safe_get(url, wait_seconds=5)
            self._scroll_down(times=2, pause=2)

            cards = self.driver.find_elements(
                By.CSS_SELECTOR,
                "li.JobsList_jobListItem__wjTHv, li[data-test='jobListing'], "
                "div.job-listing, li.react-job-listing"
            )

            logger.info(f"[Glassdoor] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Glassdoor] Parse error: {e}")
        except Exception as e:
            logger.error(f"[Glassdoor] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}
        try:
            title_el = card.find_element(By.CSS_SELECTOR, "a[data-test='job-link'], a.jobLink, a.JobCard_jobTitle__GLyJ1")
            job["title"] = title_el.text.strip()
            job["url"] = title_el.get_attribute("href")
        except NoSuchElementException:
            return None

        try:
            company_el = card.find_element(By.CSS_SELECTOR, "span.EmployerProfile_compactEmployerName__9MGcV, div.employer-name, span.job-company")
            job["company"] = company_el.text.strip()
        except NoSuchElementException:
            job["company"] = ""

        try:
            loc_el = card.find_element(By.CSS_SELECTOR, "div[data-test='emp-location'], span.job-location, div.location")
            job["location"] = loc_el.text.strip()
        except NoSuchElementException:
            job["location"] = ""

        return job

    def apply_to_job(self, job: dict, resume_path: str) -> dict:
        return {
            "status": "manual_needed",
            "message": f"Apply on Glassdoor: {job.get('url', '')}",
        }
