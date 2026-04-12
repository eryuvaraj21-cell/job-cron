"""
Indeed Job Scraper & Auto-Applier
"""

import logging
import time
import os
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)

from .base import BaseScraper

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    PLATFORM_NAME = "indeed"
    BASE_URL = "https://www.indeed.com"

    def login(self, email: str, password: str) -> bool:
        """Indeed doesn't always require login for searching. Returns True."""
        self.start()
        logger.info("[Indeed] Browser started (no login required for search)")
        return True

    def search_jobs(self, title: str, location: str) -> list:
        """Search for jobs on Indeed."""
        jobs = []
        try:
            encoded_title = quote_plus(title)
            encoded_location = quote_plus(location)

            search_url = (
                f"{self.BASE_URL}/jobs?"
                f"q={encoded_title}"
                f"&l={encoded_location}"
                f"&sort=date"
                f"&fromage=7"  # Last 7 days
            )

            self._safe_get(search_url, wait_seconds=5)
            self._scroll_down(times=2, pause=2)

            # Find job cards
            job_cards = self.driver.find_elements(
                By.CSS_SELECTOR,
                "div.job_seen_beacon, div.jobsearch-SerpJobCard, "
                "li.css-5lfssm, td.resultContent"
            )

            logger.info(f"[Indeed] Found {len(job_cards)} job cards for '{title}' in '{location}'")

            for card in job_cards[:25]:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Indeed] Error parsing card: {e}")
                    continue

        except Exception as e:
            logger.error(f"[Indeed] Search error: {e}")

        return jobs

    def _parse_job_card(self, card) -> dict:
        """Parse a single Indeed job card."""
        job = {}

        # Title and URL
        try:
            title_el = card.find_element(
                By.CSS_SELECTOR,
                "h2.jobTitle a, a.jcs-JobTitle, a[data-jk]"
            )
            job["title"] = title_el.text.strip()
            href = title_el.get_attribute("href")
            if href and href.startswith("http"):
                job["url"] = href
            else:
                job_id = title_el.get_attribute("data-jk") or ""
                if job_id:
                    job["url"] = f"{self.BASE_URL}/viewjob?jk={job_id}"
                    job["external_id"] = job_id
                else:
                    return None
        except NoSuchElementException:
            return None

        # Company
        try:
            company_el = card.find_element(
                By.CSS_SELECTOR,
                "span.companyName, span[data-testid='company-name']"
            )
            job["company"] = company_el.text.strip()
        except NoSuchElementException:
            job["company"] = ""

        # Location
        try:
            loc_el = card.find_element(
                By.CSS_SELECTOR,
                "div.companyLocation, div[data-testid='text-location']"
            )
            job["location"] = loc_el.text.strip()
        except NoSuchElementException:
            job["location"] = ""

        # Salary
        try:
            sal_el = card.find_element(
                By.CSS_SELECTOR,
                "div.salary-snippet-container, div.metadata.salary-snippet-container"
            )
            job["salary"] = sal_el.text.strip()
        except NoSuchElementException:
            job["salary"] = ""

        return job

    def apply_to_job(self, job: dict, resume_path: str) -> dict:
        """Apply to an Indeed job."""
        try:
            self._safe_get(job["url"], wait_seconds=3)
            time.sleep(2)

            # Get description
            try:
                desc_el = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "div#jobDescriptionText, div.jobsearch-jobDescriptionText"
                )
                job["description"] = desc_el.text.strip()
            except NoSuchElementException:
                job["description"] = ""

            # Look for "Apply now" or "Easy Apply" button
            apply_btn = None
            apply_selectors = [
                "button#indeedApplyButton",
                "button.indeed-apply-button",
                "button[id*='indeedApply']",
                "a[href*='apply']",
            ]

            for selector in apply_selectors:
                try:
                    apply_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if apply_btn.is_displayed():
                        break
                    apply_btn = None
                except NoSuchElementException:
                    continue

            if not apply_btn:
                # Check for external apply link
                try:
                    external_link = self.driver.find_element(
                        By.CSS_SELECTOR,
                        "a[target='_blank'][href*='apply'], "
                        "button[aria-label*='Apply']"
                    )
                    ext_url = external_link.get_attribute("href") or job["url"]
                    return {
                        "status": "manual_needed",
                        "message": f"External application required: {ext_url}",
                    }
                except NoSuchElementException:
                    return {
                        "status": "manual_needed",
                        "message": f"No apply button found: {job['url']}",
                    }

            apply_btn.click()
            time.sleep(3)

            # Handle Indeed's apply flow
            return self._handle_apply_flow(job, resume_path)

        except Exception as e:
            logger.error(f"[Indeed] Apply error for {job.get('title', 'unknown')}: {e}")
            return {"status": "failed", "message": str(e)}

    def _handle_apply_flow(self, job: dict, resume_path: str) -> dict:
        """Handle Indeed's multi-step application."""
        max_steps = 8

        for step in range(max_steps):
            time.sleep(2)

            # Check for resume upload
            try:
                file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                file_input.send_keys(os.path.abspath(resume_path))
                time.sleep(2)
            except NoSuchElementException:
                pass

            # Check for required fields we can't fill
            try:
                required_inputs = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "input[required]:not([type='hidden']):not([type='file'])"
                )
                unfilled = [
                    inp.get_attribute("name") or inp.get_attribute("aria-label") or "field"
                    for inp in required_inputs
                    if not inp.get_attribute("value")
                ]
                if unfilled:
                    return {
                        "status": "manual_needed",
                        "message": f"Additional info required ({', '.join(unfilled[:5])}): {job['url']}",
                    }
            except Exception:
                pass

            # Look for submit/continue
            try:
                continue_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[type='submit'], button.ia-continueButton, "
                    "button[aria-label='Submit your application']"
                )
                btn_text = continue_btn.text.lower()

                if "submit" in btn_text or "apply" in btn_text:
                    continue_btn.click()
                    time.sleep(3)
                    logger.info(f"[Indeed] Applied to: {job.get('title', '')} at {job.get('company', '')}")
                    return {"status": "applied", "message": "Application submitted"}
                else:
                    continue_btn.click()
                    time.sleep(1)
            except NoSuchElementException:
                pass

        return {
            "status": "manual_needed",
            "message": f"Complex application - manual completion needed: {job['url']}",
        }
