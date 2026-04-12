"""
Naukri.com Job Scraper & Auto-Applier
"""

import logging
import time
import re
import os
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


class NaukriScraper(BaseScraper):
    PLATFORM_NAME = "naukri"
    BASE_URL = "https://www.naukri.com"
    LOGIN_URL = "https://www.naukri.com/nlogin/login"

    def login(self, email: str, password: str) -> bool:
        """Login to Naukri."""
        try:
            self.start()
            self._safe_get(self.LOGIN_URL, wait_seconds=3)

            # Enter email
            email_field = self._wait_for_element(
                By.CSS_SELECTOR, "input[placeholder*='Email' i], input[placeholder*='ID' i]"
            )
            email_field.clear()
            email_field.send_keys(email)

            # Enter password
            password_field = self.driver.find_element(
                By.CSS_SELECTOR, "input[type='password']"
            )
            password_field.clear()
            password_field.send_keys(password)

            # Click login
            login_btn = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'], button.loginButton"
            )
            login_btn.click()
            time.sleep(5)

            # Check login success
            if "nlogin" not in self.driver.current_url:
                logger.info("[Naukri] Login successful")
                return True

            # Check for OTP or captcha
            page_text = self.driver.page_source.lower()
            if "otp" in page_text or "captcha" in page_text:
                logger.warning("[Naukri] OTP/Captcha detected - manual intervention needed")
                return False

            logger.warning("[Naukri] Login may have failed")
            return False

        except Exception as e:
            logger.error(f"[Naukri] Login error: {e}")
            return False

    def search_jobs(self, title: str, location: str) -> list:
        """Search for jobs on Naukri."""
        jobs = []
        try:
            encoded_title = title.replace(" ", "-").lower()
            encoded_location = location.lower()

            # Try the standard Naukri search URL format
            search_url = (
                f"{self.BASE_URL}/{encoded_title}-jobs-in-{encoded_location}"
            )

            self._safe_get(search_url, wait_seconds=5)

            # Also try the query-param based search if no results
            self._scroll_down(times=3, pause=2)

            # Find job cards (Naukri has multiple layouts)
            job_cards = self.driver.find_elements(
                By.CSS_SELECTOR,
                "article.jobTuple, div.srp-jobtuple-wrapper, div.cust-job-tuple, "
                "div[class*='jobTuple'], div[data-job-id], "
                "div.styles_jlc__main__VdwtF, div[class*='styles_job-listing'], "
                "a.title, div.list, div.jobTupleHeader"
            )

            # If still empty, try broader XPath
            if not job_cards:
                job_cards = self.driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class,'tuple')]|//div[contains(@class,'job')]//a[contains(@href,'/job-listings')]/.."
                )

            logger.info(f"[Naukri] Found {len(job_cards)} job cards for '{title}' in '{location}'")

            for card in job_cards[:25]:
                try:
                    job = self._parse_job_card(card)
                    if job:
                        job["platform"] = self.PLATFORM_NAME
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"[Naukri] Error parsing card: {e}")
                    continue

        except Exception as e:
            logger.error(f"[Naukri] Search error: {e}")

        return jobs

    def _parse_job_card(self, card) -> dict:
        """Parse a single Naukri job card."""
        job = {}

        # Title and URL
        try:
            title_el = card.find_element(
                By.CSS_SELECTOR,
                "a.title, a.loc_title, a[class*='title'], "
                "h2 a, a[href*='job-listings']"
            )
            job["title"] = title_el.text.strip()
            job["url"] = title_el.get_attribute("href")
        except NoSuchElementException:
            return None

        if not job.get("title"):
            return None

        # Company
        try:
            company_el = card.find_element(
                By.CSS_SELECTOR,
                "a.subTitle, span.comp-name, a.comp-name, "
                "a[class*='comp'], span[class*='comp'], "
                "a[class*='subTitle']"
            )
            job["company"] = company_el.text.strip()
        except NoSuchElementException:
            job["company"] = ""

        # Location
        try:
            loc_el = card.find_element(By.CSS_SELECTOR, "span.loc, span.locWdth, li.location")
            job["location"] = loc_el.text.strip()
        except NoSuchElementException:
            job["location"] = ""

        # Experience
        try:
            exp_el = card.find_element(By.CSS_SELECTOR, "span.exp, span.expwdth, li.experience")
            job["experience"] = exp_el.text.strip()
        except NoSuchElementException:
            job["experience"] = ""

        # Salary
        try:
            sal_el = card.find_element(By.CSS_SELECTOR, "span.sal, li.salary")
            job["salary"] = sal_el.text.strip()
        except NoSuchElementException:
            job["salary"] = ""

        # Skills / Tags
        try:
            tag_els = card.find_elements(By.CSS_SELECTOR, "li.tag, span.tag, ul.tags li")
            job["skills_required"] = [t.text.strip() for t in tag_els if t.text.strip()]
        except NoSuchElementException:
            job["skills_required"] = []

        # Extract ID from URL
        if job.get("url"):
            match = re.search(r"-(\d+)\??", job["url"])
            if match:
                job["external_id"] = match.group(1)

        return job

    def apply_to_job(self, job: dict, resume_path: str) -> dict:
        """Apply to a job on Naukri."""
        try:
            self._safe_get(job["url"], wait_seconds=3)
            time.sleep(2)

            # Get job description
            try:
                desc_el = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "div.job-desc, section.job-desc, div.jd-desc"
                )
                job["description"] = desc_el.text.strip()
            except NoSuchElementException:
                job["description"] = ""

            # Look for Apply button
            apply_btn = None
            apply_selectors = [
                "button#apply-button",
                "button.apply-button",
                "button[id*='apply']",
                "a[id*='apply']",
                "button.chatbot-apply",
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
                # Check if already applied
                page_text = self.driver.page_source.lower()
                if "already applied" in page_text or "applied successfully" in page_text:
                    return {"status": "already_applied", "message": "Already applied to this job"}

                return {
                    "status": "manual_needed",
                    "message": f"No apply button found. May require external application: {job['url']}",
                }

            apply_btn.click()
            time.sleep(3)

            # Check if it opened an external link or a form
            current_url = self.driver.current_url

            # If redirected to company portal
            if "naukri.com" not in current_url:
                return {
                    "status": "manual_needed",
                    "message": f"Redirected to company portal: {current_url}",
                }

            # Check for chatbot/questionnaire
            try:
                chatbot = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "div.chatbot_container, div.questionnaire, form.apply-form"
                )
                if chatbot.is_displayed():
                    return {
                        "status": "manual_needed",
                        "message": f"Application has additional questions/chatbot: {job['url']}",
                    }
            except NoSuchElementException:
                pass

            # Check for success message
            page_text = self.driver.page_source.lower()
            if "applied successfully" in page_text or "application submitted" in page_text:
                logger.info(f"[Naukri] Applied to: {job.get('title', '')} at {job.get('company', '')}")
                return {"status": "applied", "message": "Application submitted successfully"}

            # Upload resume if prompted
            try:
                file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                file_input.send_keys(os.path.abspath(resume_path))
                time.sleep(2)

                # Submit
                submit_btn = self.driver.find_element(
                    By.CSS_SELECTOR, "button[type='submit'], button.submit"
                )
                submit_btn.click()
                time.sleep(3)
                return {"status": "applied", "message": "Application submitted with resume"}
            except NoSuchElementException:
                pass

            return {"status": "applied", "message": "Apply button clicked - checking status"}

        except Exception as e:
            logger.error(f"[Naukri] Apply error for {job.get('title', 'unknown')}: {e}")
            return {"status": "failed", "message": str(e)}

    def update_profile_resume(self, resume_path: str) -> bool:
        """Update resume on Naukri profile (keeps profile active)."""
        try:
            self._safe_get("https://www.naukri.com/mnjuser/profile", wait_seconds=5)

            # Find resume upload area
            try:
                upload_el = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "input[type='file']#attachCV, input.fileUpload"
                )
                upload_el.send_keys(os.path.abspath(resume_path))
                time.sleep(5)
                logger.info("[Naukri] Resume updated on profile")
                return True
            except NoSuchElementException:
                logger.warning("[Naukri] Could not find resume upload element")
                return False

        except Exception as e:
            logger.error(f"[Naukri] Profile update error: {e}")
            return False
