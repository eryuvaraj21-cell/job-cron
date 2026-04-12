"""
Google Jobs Scraper (Aggregator - pulls from many sites)
"""

import logging
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from .base import BaseScraper

logger = logging.getLogger(__name__)


class GoogleJobsScraper(BaseScraper):
    PLATFORM_NAME = "google_jobs"
    BASE_URL = "https://www.google.com/search"

    def login(self, email: str, password: str) -> bool:
        self.start()
        logger.info("[GoogleJobs] Browser started")
        return True

    def search_jobs(self, title: str, location: str) -> list:
        jobs = []
        try:
            query = f"{title} jobs in {location}"
            url = f"{self.BASE_URL}?q={quote_plus(query)}&ibp=htl;jobs"

            self._safe_get(url, wait_seconds=5)
            self._scroll_down(times=2, pause=2)

            cards = self.driver.find_elements(By.CSS_SELECTOR, "li.iFjolb, div.PwjeAc")

            logger.info(f"[GoogleJobs] Found {len(cards)} jobs for '{title}' in '{location}'")

            for card in cards[:20]:
                try:
                    card.click()
                    import time
                    time.sleep(1)
                    job = self._parse_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[GoogleJobs] Parse error: {e}")
        except Exception as e:
            logger.error(f"[GoogleJobs] Search error: {e}")
        return jobs

    def _parse_card(self, card) -> dict:
        job = {}
        try:
            title_el = card.find_element(By.CSS_SELECTOR, "div.BjJfJf, h2.KLsYvd")
            job["title"] = title_el.text.strip()
        except NoSuchElementException:
            return None

        try:
            company_el = card.find_element(By.CSS_SELECTOR, "div.vNEEBe, div.nJlQNd")
            job["company"] = company_el.text.strip()
        except NoSuchElementException:
            job["company"] = ""

        try:
            loc_el = card.find_element(By.CSS_SELECTOR, "div.Qk80Jf, div.sMbDJe")
            job["location"] = loc_el.text.strip()
        except NoSuchElementException:
            job["location"] = ""

        # Try to get apply link from detail pane
        try:
            apply_link = self.driver.find_element(
                By.CSS_SELECTOR,
                "a.pMhGee, a[data-ved][href*='apply'], a[class*='apply']"
            )
            job["url"] = apply_link.get_attribute("href")
        except NoSuchElementException:
            job["url"] = f"https://www.google.com/search?q={job['title']}+{job.get('company','')}+jobs&ibp=htl;jobs"

        return job

    def apply_to_job(self, job: dict, resume_path: str) -> dict:
        return {
            "status": "manual_needed",
            "message": f"Apply via Google Jobs: {job.get('url', '')}",
        }
