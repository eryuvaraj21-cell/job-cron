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
        if not email or not password:
            logger.error("[Naukri] Missing credentials. Set NAUKRI_EMAIL and NAUKRI_PASSWORD")
            return False
        try:
            self.start()
            self._safe_get(self.LOGIN_URL, wait_seconds=4)

            # Naukri login form uses ids 'usernameField' and 'passwordField'.
            # Fall back to common selectors if ids are not present.
            email_field = None
            for locator in [
                (By.ID, "usernameField"),
                (By.NAME, "email"),
                (By.CSS_SELECTOR, "input[placeholder*='Email' i]"),
                (By.CSS_SELECTOR, "input[placeholder*='Username' i]"),
                (By.CSS_SELECTOR, "form input[type='text']"),
            ]:
                try:
                    email_field = self._wait_for_element(*locator, timeout=8)
                    if email_field and email_field.is_displayed():
                        break
                except TimeoutException:
                    continue
            if not email_field:
                logger.error("[Naukri] Could not locate email field")
                if not self.headless:
                    self._keep_open_on_failure = True
                return False

            if not self._type_into(email_field, email):
                logger.warning("[Naukri] Failed to type email reliably")

            password_field = None
            for locator in [
                (By.ID, "passwordField"),
                (By.NAME, "password"),
                (By.CSS_SELECTOR, "input[type='password']"),
            ]:
                try:
                    password_field = self.driver.find_element(*locator)
                    if password_field and password_field.is_displayed():
                        break
                except NoSuchElementException:
                    continue
            if not password_field:
                logger.error("[Naukri] Could not locate password field")
                if not self.headless:
                    self._keep_open_on_failure = True
                return False

            if not self._type_into(password_field, password):
                logger.warning("[Naukri] Failed to type password reliably")

            # Click login
            try:
                login_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[@type='submit' or contains(translate(., 'LOGIN', 'login'), 'login')]",
                )
                login_btn.click()
            except NoSuchElementException:
                password_field.send_keys(Keys.RETURN)

            time.sleep(6)

            # Handle OTP if requested
            if self._handle_otp_if_present():
                time.sleep(5)

            # Check login success
            if "nlogin" not in self.driver.current_url:
                logger.info("[Naukri] Login successful")
                return True

            page_text = self.driver.page_source.lower()
            if "captcha" in page_text:
                logger.warning("[Naukri] Captcha detected - manual intervention needed")
                if not self.headless:
                    self._keep_open_on_failure = True
                return False

            logger.warning("[Naukri] Login may have failed")
            if not self.headless:
                self._keep_open_on_failure = True
            return False

        except Exception as e:
            logger.error(f"[Naukri] Login error: {e}")
            return False

    def _handle_otp_if_present(self) -> bool:
        """If Naukri shows an OTP screen, fetch OTP from email and submit. Returns True if handled."""
        try:
            page_text = self.driver.page_source.lower()
            if "otp" not in page_text and "verification code" not in page_text:
                return False
            otp_input = None
            for sel in [
                "input[name*='otp' i]",
                "input[id*='otp' i]",
                "input[placeholder*='OTP' i]",
                "input[autocomplete='one-time-code']",
                "input[maxlength='6']",
            ]:
                try:
                    el = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if el.is_displayed():
                        otp_input = el
                        break
                except NoSuchElementException:
                    continue
            if not otp_input:
                return False

            logger.info("[Naukri] OTP screen detected - fetching OTP from email")
            otp = self.fetch_otp_from_email(
                sender_filters=["naukri.com", "no-reply@naukri.com"],
                subject_keywords=["otp", "verification", "naukri"],
            )
            if not otp:
                logger.warning("[Naukri] OTP not received from email")
                if not self.headless:
                    self._keep_open_on_failure = True
                return False
            self._type_into(otp_input, otp, per_char_delay=0.08)
            try:
                submit = self.driver.find_element(
                    By.XPATH,
                    "//button[@type='submit' or contains(translate(., 'VERIFY', 'verify'), 'verify') or contains(translate(., 'SUBMIT', 'submit'), 'submit')]",
                )
                submit.click()
            except NoSuchElementException:
                otp_input.send_keys(Keys.RETURN)
            return True
        except Exception as e:
            logger.warning(f"[Naukri] OTP handling error: {e}")
            return False

    def get_recommended_jobs(self, max_pages: int = 5) -> list:
        """Scrape jobs from Naukri 'Recommended jobs for you' page (requires login).

        The recommended page renders cards as <article class="jobTuple" data-job-id="..">
        WITHOUT an inner <a href="/job-listings.."> anchor — clicking the card
        navigates via JS. We collect each card's metadata and open it in a new
        tab to capture the real job URL.
        """
        jobs = []
        seen_ids = set()
        try:
            self._safe_get("https://www.naukri.com/mnjuser/recommendedjobs", wait_seconds=5)
            time.sleep(3)

            # Iterate over the four tabs on the recommended page
            tab_ids = ["profile", "top_candidate", "preference", "similar_jobs"]
            for tab_id in tab_ids:
                try:
                    tab = self.driver.find_element(By.ID, tab_id)
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab)
                    time.sleep(0.3)
                    try:
                        tab.click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", tab)
                    time.sleep(2)
                    logger.info(f"[Naukri] Switched to recommended tab '{tab_id}'")
                except NoSuchElementException:
                    logger.debug(f"[Naukri] Tab '{tab_id}' not found, skipping")
                    continue
                except Exception as e:
                    logger.debug(f"[Naukri] Could not click tab '{tab_id}': {e}")
                    continue

                # Scroll to load all cards in this tab
                self._scroll_down(times=10, pause=1.2)

                # Find ONLY genuine job tuples (filter out promo widgets)
                cards = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "div.reco-container article.jobTuple[data-job-id], "
                    "div.sim-jobs article.jobTuple[data-job-id], "
                    "article.jobTuple[data-job-id]",
                )
                logger.info(f"[Naukri] Tab '{tab_id}': {len(cards)} job cards")

                # Collect static metadata + job IDs first (DOM may go stale after click)
                tab_card_data = []
                for card in cards:
                    try:
                        job_id = card.get_attribute("data-job-id")
                        if not job_id or job_id in seen_ids:
                            continue
                        # Skip promo / widget tuples
                        try:
                            card.find_element(By.XPATH, "ancestor::div[contains(@id,'naukri-wdgt') or contains(@class,'reco-job-promotion')]")
                            continue
                        except NoSuchElementException:
                            pass

                        # Title
                        title = ""
                        try:
                            t_el = card.find_element(By.CSS_SELECTOR, "p.title, a.title")
                            title = (t_el.get_attribute("title") or t_el.text or "").strip()
                        except NoSuchElementException:
                            pass
                        if not title:
                            continue

                        # Company
                        company = ""
                        try:
                            c_el = card.find_element(By.CSS_SELECTOR, "span.subTitle, a.subTitle")
                            company = (c_el.get_attribute("title") or c_el.text or "").strip()
                        except NoSuchElementException:
                            pass

                        # Location
                        location = ""
                        try:
                            l_el = card.find_element(By.CSS_SELECTOR, "li.placeHolderLi.location span, li.location span, span.locWdth")
                            location = (l_el.get_attribute("title") or l_el.text or "").strip()
                        except NoSuchElementException:
                            pass

                        # Experience
                        experience = ""
                        try:
                            e_el = card.find_element(By.CSS_SELECTOR, "li.placeHolderLi.experience span, li.experience span, span.expwdth")
                            experience = (e_el.get_attribute("title") or e_el.text or "").strip()
                        except NoSuchElementException:
                            pass

                        # Salary
                        salary = ""
                        try:
                            s_el = card.find_element(By.CSS_SELECTOR, "li.placeHolderLi.salary span, li.salary span")
                            salary = (s_el.get_attribute("title") or s_el.text or "").strip()
                        except NoSuchElementException:
                            pass

                        # Tags / skills
                        skills = []
                        try:
                            tag_els = card.find_elements(By.CSS_SELECTOR, "ul.tags li, li.tag, span.tag")
                            skills = [(t.get_attribute("title") or t.text or "").strip() for t in tag_els]
                            skills = [s for s in skills if s]
                        except Exception:
                            pass

                        tab_card_data.append({
                            "external_id": job_id,
                            "title": title,
                            "company": company,
                            "location": location,
                            "experience": experience,
                            "salary": salary,
                            "skills_required": skills,
                        })
                    except Exception as e:
                        logger.debug(f"[Naukri] Error reading recommended card: {e}")
                        continue

                logger.info(f"[Naukri] Tab '{tab_id}': collected metadata for {len(tab_card_data)} unique cards")

                # Now resolve each job's URL by opening the card in a new tab
                main_handle = self.driver.current_window_handle
                for data in tab_card_data:
                    job_id = data["external_id"]
                    if job_id in seen_ids:
                        continue
                    url = None
                    try:
                        # Re-find the card (DOM may have shifted)
                        card_el = None
                        try:
                            card_el = self.driver.find_element(
                                By.CSS_SELECTOR,
                                f"article.jobTuple[data-job-id='{job_id}']",
                            )
                        except NoSuchElementException:
                            pass

                        if card_el is not None:
                            # Find the title link/element to ctrl+click open
                            click_target = None
                            for sel in ["p.title", "a.title", "div.info"]:
                                try:
                                    click_target = card_el.find_element(By.CSS_SELECTOR, sel)
                                    break
                                except NoSuchElementException:
                                    continue
                            if click_target is None:
                                click_target = card_el

                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", click_target)
                            time.sleep(0.2)

                            handles_before = set(self.driver.window_handles)
                            # Open in new tab via ctrl+click
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                from selenium.webdriver.common.keys import Keys
                                ActionChains(self.driver).key_down(Keys.CONTROL).click(click_target).key_up(Keys.CONTROL).perform()
                            except Exception:
                                # Fallback: regular click then go back
                                try:
                                    click_target.click()
                                except ElementClickInterceptedException:
                                    self.driver.execute_script("arguments[0].click();", click_target)
                            time.sleep(2)

                            new_handles = set(self.driver.window_handles) - handles_before
                            if new_handles:
                                # Switch to new tab, grab URL, close it
                                new_h = new_handles.pop()
                                self.driver.switch_to.window(new_h)
                                time.sleep(1.5)
                                url = self.driver.current_url
                                try:
                                    self.driver.close()
                                except Exception:
                                    pass
                                self.driver.switch_to.window(main_handle)
                            else:
                                # Same-tab navigation happened
                                time.sleep(1)
                                url = self.driver.current_url
                                if "recommendedjobs" not in url:
                                    self.driver.back()
                                    time.sleep(2)
                                else:
                                    url = None

                        if url and "naukri.com" in url and "recommendedjobs" not in url:
                            seen_ids.add(job_id)
                            data["url"] = url
                            data["platform"] = self.PLATFORM_NAME
                            jobs.append(data)
                        else:
                            logger.debug(f"[Naukri] Could not resolve URL for job_id {job_id}")
                    except Exception as e:
                        logger.debug(f"[Naukri] Error resolving URL for job_id {job_id}: {e}")
                        # Make sure we're back on the main tab
                        try:
                            if self.driver.current_window_handle != main_handle:
                                self.driver.close()
                                self.driver.switch_to.window(main_handle)
                        except Exception:
                            pass
                        continue

                logger.info(f"[Naukri] Tab '{tab_id}': resolved {sum(1 for j in jobs if j.get('external_id') in {d['external_id'] for d in tab_card_data})} URLs (running total: {len(jobs)})")
        except Exception as e:
            logger.error(f"[Naukri] Recommended jobs error: {e}")
        logger.info(f"[Naukri] Total recommended jobs collected: {len(jobs)}")
        return jobs

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
                "button.styles_apply-button__uJI_J",
                "button[class*='apply-button']",
                "button[class*='Apply']",
            ]

            for selector in apply_selectors:
                try:
                    els = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        try:
                            if el.is_displayed() and el.is_enabled():
                                apply_btn = el
                                break
                        except Exception:
                            continue
                    if apply_btn:
                        break
                except Exception:
                    continue

            # Text-based fallback
            if not apply_btn:
                try:
                    btns = self.driver.find_elements(By.XPATH, "//button | //a")
                    for b in btns:
                        try:
                            txt = (b.text or "").strip().lower()
                            if txt in ("apply", "apply now", "easy apply", "i'm interested"):
                                if b.is_displayed():
                                    apply_btn = b
                                    break
                        except Exception:
                            continue
                except Exception:
                    pass

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
