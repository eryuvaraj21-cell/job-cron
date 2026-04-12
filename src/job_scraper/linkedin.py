"""
LinkedIn Job Scraper & Auto-Applier
"""

import logging
import time
import re
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
)

from .base import BaseScraper

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    PLATFORM_NAME = "linkedin"
    BASE_URL = "https://www.linkedin.com"
    LOGIN_URL = "https://www.linkedin.com/login"
    JOBS_URL = "https://www.linkedin.com/jobs/search/"

    def login(self, email: str, password: str) -> bool:
        """Login to LinkedIn."""
        try:
            self.start()
            self._safe_get(self.LOGIN_URL, wait_seconds=3)

            email_field = self._wait_for_element(By.ID, "username")
            email_field.clear()
            email_field.send_keys(email)

            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)

            password_field.send_keys(Keys.RETURN)
            time.sleep(5)

            # Check if login was successful
            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                logger.info("[LinkedIn] Login successful")
                return True

            # Check for security challenge
            if "checkpoint" in self.driver.current_url or "challenge" in self.driver.current_url:
                logger.warning("[LinkedIn] Security challenge detected - manual intervention needed")
                return False

            logger.warning(f"[LinkedIn] Login may have failed. Current URL: {self.driver.current_url}")
            return False

        except Exception as e:
            logger.error(f"[LinkedIn] Login error: {e}")
            return False

    def search_jobs(self, title: str, location: str) -> list:
        """Search for jobs on LinkedIn."""
        jobs = []
        try:
            encoded_title = quote_plus(title)
            encoded_location = quote_plus(location)

            # f_AL=true filters for Easy Apply jobs
            search_url = (
                f"{self.JOBS_URL}?keywords={encoded_title}"
                f"&location={encoded_location}"
                f"&f_AL=true"  # Easy Apply filter
                f"&f_TPR=r604800"  # Past week
                f"&sortBy=DD"  # Sort by date
            )

            self._safe_get(search_url, wait_seconds=5)
            self._scroll_down(times=3, pause=2)

            # Find job cards
            job_cards = self.driver.find_elements(
                By.CSS_SELECTOR,
                "div.job-card-container, li.jobs-search-results__list-item"
            )

            logger.info(f"[LinkedIn] Found {len(job_cards)} job cards for '{title}' in '{location}'")

            for card in job_cards[:25]:  # Limit per search
                try:
                    job = self._parse_job_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[LinkedIn] Error parsing card: {e}")
                    continue

        except Exception as e:
            logger.error(f"[LinkedIn] Search error: {e}")

        return jobs

    def _parse_job_card(self, card) -> dict:
        """Parse a single job card element."""
        job = {}

        try:
            title_el = card.find_element(
                By.CSS_SELECTOR,
                "a.job-card-list__title, a.job-card-container__link"
            )
            job["title"] = title_el.text.strip()
            job["url"] = title_el.get_attribute("href").split("?")[0]
        except NoSuchElementException:
            return None

        try:
            company_el = card.find_element(
                By.CSS_SELECTOR,
                "span.job-card-container__primary-description, "
                "a.job-card-container__company-name"
            )
            job["company"] = company_el.text.strip()
        except NoSuchElementException:
            job["company"] = ""

        try:
            location_el = card.find_element(
                By.CSS_SELECTOR,
                "li.job-card-container__metadata-item"
            )
            job["location"] = location_el.text.strip()
        except NoSuchElementException:
            job["location"] = ""

        # Extract job ID from URL
        if job.get("url"):
            match = re.search(r"/view/(\d+)", job["url"])
            if match:
                job["external_id"] = match.group(1)

        return job

    def _get_job_description(self) -> str:
        """Get the full job description from the detail pane."""
        try:
            desc_el = self._wait_for_element(
                By.CSS_SELECTOR,
                "div.jobs-description-content__text, div.jobs-description__content",
                timeout=5,
            )
            return desc_el.text.strip()
        except TimeoutException:
            return ""

    def apply_to_job(self, job: dict, resume_path: str) -> dict:
        """Apply to a LinkedIn Easy Apply job."""
        try:
            self._safe_get(job["url"], wait_seconds=3)
            time.sleep(2)

            # Look for Easy Apply button
            try:
                apply_btn = self._wait_for_clickable(
                    By.CSS_SELECTOR,
                    "button.jobs-apply-button, button[aria-label*='Easy Apply']",
                    timeout=10,
                )
            except TimeoutException:
                return {
                    "status": "manual_needed",
                    "message": f"No Easy Apply button found. External application required: {job['url']}",
                }

            # Get description before applying
            description = self._get_job_description()
            job["description"] = description

            apply_btn.click()
            time.sleep(2)

            # Handle the Easy Apply modal
            return self._handle_easy_apply_modal(job, resume_path)

        except Exception as e:
            logger.error(f"[LinkedIn] Apply error for {job.get('title', 'unknown')}: {e}")
            return {"status": "failed", "message": str(e)}

    def _handle_easy_apply_modal(self, job: dict, resume_path: str) -> dict:
        """Handle the LinkedIn Easy Apply multi-step modal."""
        max_steps = 10

        for step in range(max_steps):
            time.sleep(1.5)

            # Check if there's a submit button (final step)
            try:
                submit_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Submit application'], "
                    "button[aria-label='Review your application']"
                )

                if "Submit" in submit_btn.text:
                    submit_btn.click()
                    time.sleep(3)

                    # Check for success
                    try:
                        self.driver.find_element(
                            By.CSS_SELECTOR,
                            "div[aria-label*='applied'], h2.t-bold"
                        )
                        logger.info(f"[LinkedIn] Successfully applied to: {job.get('title', '')} at {job.get('company', '')}")
                        return {"status": "applied", "message": "Successfully applied via Easy Apply"}
                    except NoSuchElementException:
                        pass

                    return {"status": "applied", "message": "Application submitted"}

                elif "Review" in submit_btn.text:
                    submit_btn.click()
                    time.sleep(1)
                    continue

            except NoSuchElementException:
                pass

            # Check for additional questions that need manual input
            try:
                text_inputs = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "input[type='text']:not([value]), "
                    "textarea:not(:disabled)"
                )
                required_unfilled = []
                for inp in text_inputs:
                    if inp.get_attribute("required") and not inp.get_attribute("value"):
                        required_unfilled.append(inp.get_attribute("aria-label") or "unknown field")

                if required_unfilled:
                    # Close the modal
                    self._close_modal()
                    return {
                        "status": "manual_needed",
                        "message": f"Additional fields required: {', '.join(required_unfilled)}. URL: {job['url']}",
                    }
            except Exception:
                pass

            # Try to proceed to next step
            try:
                next_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Continue to next step'], "
                    "button[data-easy-apply-next-button]"
                )
                next_btn.click()
                time.sleep(1)
            except NoSuchElementException:
                pass

        # If we exhausted all steps, it needs manual attention
        self._close_modal()
        return {
            "status": "manual_needed",
            "message": f"Complex application form detected. URL: {job['url']}",
        }

    def _close_modal(self):
        """Close the Easy Apply modal."""
        try:
            close_btn = self.driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label='Dismiss'], button.artdeco-modal__dismiss"
            )
            close_btn.click()
            time.sleep(1)

            # Confirm discard
            try:
                discard_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[data-control-name='discard_application_confirm_btn'], "
                    "button[data-test-dialog-primary-btn]"
                )
                discard_btn.click()
            except NoSuchElementException:
                pass
        except NoSuchElementException:
            pass
