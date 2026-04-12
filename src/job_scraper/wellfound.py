"""
Wellfound (formerly AngelList Talent) Job Scraper
"""

import logging
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from .base import BaseScraper

logger = logging.getLogger(__name__)


class WellfoundScraper(BaseScraper):
    PLATFORM_NAME = "wellfound"
    BASE_URL = "https://wellfound.com"

    def login(self, email: str, password: str) -> bool:
        self.start()
        logger.info("[Wellfound] Browser started (no login needed for search)")
        return True

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            encoded_title = quote_plus(title)
            url = f"{self.BASE_URL}/jobs?query={encoded_title}&location={quote_plus(location)}"

            self._safe_get(url, wait_seconds=5)
            self._scroll_down(times=3, pause=2)

            cards = self.driver.find_elements(
                By.CSS_SELECTOR,
                "div[class*='styles_jobListing'], div.job-listing, "
                "div[data-test='job-listing'], a[class*='JobSearchResult']"
            )

            logger.info(f"[Wellfound] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"[Wellfound] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}
        try:
            title_el = card.find_element(By.CSS_SELECTOR, "a[class*='title'], h4 a, a[href*='/jobs/']")
            job["title"] = title_el.text.strip()
            job["url"] = title_el.get_attribute("href")
        except NoSuchElementException:
            return None

        try:
            company_el = card.find_element(By.CSS_SELECTOR, "a[class*='company'], h3, span[class*='company']")
            job["company"] = company_el.text.strip()
        except NoSuchElementException:
            job["company"] = ""

        try:
            loc_el = card.find_element(By.CSS_SELECTOR, "span[class*='location']")
            job["location"] = loc_el.text.strip()
        except NoSuchElementException:
            job["location"] = ""

        return job

    def apply_to_job(self, job: dict, resume_path: str) -> dict:
        return {
            "status": "manual_needed",
            "message": f"Apply on Wellfound: {job.get('url', '')}",
        }
