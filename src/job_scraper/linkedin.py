"""
LinkedIn Job Scraper & Auto-Applier
"""

import logging
import os
import time
import re
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    InvalidSessionIdException,
    WebDriverException,
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
        if not email or not password:
            logger.error("[LinkedIn] Missing credentials. Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD")
            return False
        try:
            self.start()
            self._safe_get(self.LOGIN_URL, wait_seconds=4)

            # Locate email field with fallbacks
            email_field = None
            for locator in [
                (By.ID, "username"),
                (By.NAME, "session_key"),
                (By.CSS_SELECTOR, "input#username"),
                (By.CSS_SELECTOR, "input[name='session_key']"),
                (By.CSS_SELECTOR, "input[autocomplete='username']"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ]:
                try:
                    el = self._wait_for_element(*locator, timeout=8)
                    if el and el.is_displayed():
                        email_field = el
                        break
                except TimeoutException:
                    continue
            if not email_field:
                try:
                    cur_url = self.driver.current_url
                    cur_title = self.driver.title
                except Exception:
                    cur_url = cur_title = "<unavailable>"
                # Maybe already logged in (LinkedIn redirected away from /login)
                if "feed" in (cur_url or "") or "linkedin.com/in/" in (cur_url or ""):
                    logger.info(f"[LinkedIn] Already logged in (url={cur_url}). Skipping login.")
                    return True
                logger.error(f"[LinkedIn] Could not locate email field. url={cur_url} title={cur_title!r}")
                if not self.headless:
                    self._keep_open_on_failure = True
                return False

            if not self._type_into(email_field, email):
                logger.warning("[LinkedIn] Failed to type email reliably")

            # Locate password field
            password_field = None
            for locator in [
                (By.ID, "password"),
                (By.NAME, "session_password"),
                (By.CSS_SELECTOR, "input[type='password']"),
            ]:
                try:
                    el = self.driver.find_element(*locator)
                    if el and el.is_displayed():
                        password_field = el
                        break
                except NoSuchElementException:
                    continue
            if not password_field:
                logger.error("[LinkedIn] Could not locate password field on login page")
                if not self.headless:
                    self._keep_open_on_failure = True
                return False

            if not self._type_into(password_field, password):
                logger.warning("[LinkedIn] Failed to type password reliably")

            # Click submit button if available, else press Enter
            try:
                submit_btn = self.driver.find_element(
                    By.CSS_SELECTOR, "button[type='submit'], button[aria-label='Sign in']"
                )
                submit_btn.click()
            except NoSuchElementException:
                password_field.send_keys(Keys.RETURN)

            time.sleep(6)

            # Handle OTP/email verification if requested
            if self._handle_otp_if_present():
                time.sleep(5)

            # Check if login was successful
            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                logger.info("[LinkedIn] Login successful")
                return True

            # Check for security challenge
            if "checkpoint" in self.driver.current_url or "challenge" in self.driver.current_url:
                logger.warning("[LinkedIn] Security challenge detected - manual intervention needed")
                if not self.headless:
                    logger.warning("[LinkedIn] Browser left open for you to complete the challenge manually")
                    self._keep_open_on_failure = True
                return False

            logger.warning(f"[LinkedIn] Login may have failed. Current URL: {self.driver.current_url}")
            if not self.headless:
                self._keep_open_on_failure = True
            return False

        except Exception as e:
            logger.error(f"[LinkedIn] Login error: {e!r}", exc_info=True)
            if not self.headless:
                self._keep_open_on_failure = True
            return False

    def _handle_otp_if_present(self) -> bool:
        """If LinkedIn shows an OTP/PIN screen, fetch from email and submit."""
        try:
            url = self.driver.current_url
            page_text = self.driver.page_source.lower()
            triggers = ("checkpoint", "challenge", "verification", "two-step", "pin", "verify it's you", "enter the code")
            if not any(t in url.lower() or t in page_text for t in triggers):
                return False
            otp_input = None
            for sel in [
                "input[name='pin']",
                "input[id*='pin' i]",
                "input[autocomplete='one-time-code']",
                "input[name='challengeId']",
                "input[type='text'][maxlength='6']",
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
            logger.info("[LinkedIn] OTP/verification screen detected - fetching OTP from email")
            otp = self.fetch_otp_from_email(
                sender_filters=["linkedin.com", "security-noreply@linkedin.com"],
                subject_keywords=["linkedin", "verification", "code", "pin"],
            )
            if not otp:
                logger.warning("[LinkedIn] OTP not received from email")
                if not self.headless:
                    self._keep_open_on_failure = True
                return False
            self._type_into(otp_input, otp, per_char_delay=0.08)
            try:
                submit = self.driver.find_element(
                    By.XPATH,
                    "//button[@type='submit' or contains(translate(., 'SUBMIT', 'submit'), 'submit') or contains(translate(., 'VERIFY', 'verify'), 'verify')]",
                )
                submit.click()
            except NoSuchElementException:
                otp_input.send_keys(Keys.RETURN)
            return True
        except Exception as e:
            logger.warning(f"[LinkedIn] OTP handling error: {e}")
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

            # Look for Easy Apply button (try several modern selectors + text fallback)
            apply_btn = None
            selectors = [
                "button.jobs-apply-button",
                "button[aria-label*='Easy Apply']",
                "button[aria-label*='easy apply' i]",
                "div.jobs-apply-button--top-card button",
                "button.jobs-s-apply__button",
            ]
            for sel in selectors:
                try:
                    apply_btn = self._wait_for_clickable(By.CSS_SELECTOR, sel, timeout=4)
                    if apply_btn:
                        break
                except TimeoutException:
                    continue
            if not apply_btn:
                # Fallback: scan all buttons for "Easy Apply" text
                try:
                    btns = self.driver.find_elements(By.TAG_NAME, "button")
                    for b in btns:
                        try:
                            txt = (b.text or "").strip().lower()
                            if "easy apply" in txt:
                                apply_btn = b
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
            if not apply_btn:
                return {
                    "status": "manual_needed",
                    "message": f"No Easy Apply button found. External application required: {job['url']}",
                }

            # Get description before applying
            description = self._get_job_description()
            job["description"] = description

            # Skip if already applied
            try:
                btn_text = (apply_btn.text or "").lower()
                if "applied" in btn_text:
                    return {"status": "already_applied", "message": "Already applied"}
            except Exception:
                pass

            try:
                apply_btn.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", apply_btn)
            time.sleep(2)

            # Handle the Easy Apply modal
            return self._handle_easy_apply_modal(job, resume_path)

        except Exception as e:
            logger.error(f"[LinkedIn] Apply error for {job.get('title', 'unknown')}: {e}")
            return {"status": "failed", "message": str(e)}

    # ── Easy Apply form-filling helpers ────────────────────────────

    def _profile_value_for_label(self, label: str) -> str:
        """Map common form labels to a sensible value from the resume profile."""
        from src.main import HARDCODED  # lazy import to avoid circular at module load
        l = (label or "").lower()
        years = str(int(getattr(self, "_profile_years", 0) or 0))
        if any(k in l for k in ["mobile", "phone", "contact number"]):
            return HARDCODED.get("YOUR_PHONE", "9999999999").replace("+", "").replace("-", "").replace(" ", "")
        if "email" in l:
            return HARDCODED.get("YOUR_EMAIL", "")
        if "first name" in l:
            return HARDCODED.get("YOUR_NAME", "User").split()[0]
        if "last name" in l:
            parts = HARDCODED.get("YOUR_NAME", "User").split()
            return parts[-1] if len(parts) > 1 else ""
        if "name" in l:
            return HARDCODED.get("YOUR_NAME", "User")
        if "city" in l or "location" in l:
            return "Bangalore"
        if "linkedin" in l:
            return "https://www.linkedin.com/in/yuvaraj"
        if "github" in l or "portfolio" in l or "website" in l:
            return "https://github.com/"
        if "salary" in l or "ctc" in l or "compensation" in l:
            return "1500000"
        if "notice" in l:
            return "30"
        if any(k in l for k in ["experience", "years"]):
            return years or "4"
        if "willing" in l or "relocate" in l or "authorized" in l or "eligible" in l or "english" in l:
            return "Yes"
        return years or "4"  # default for any numeric/unknown question

    def _select_best_option(self, label: str, option_texts: list) -> str:
        """Pick the best dropdown/radio option for a label from available options."""
        if not option_texts:
            return ""
        l = (label or "").lower()
        opts_lower = [o.lower() for o in option_texts]
        # Skip placeholder option like "Select an option"
        usable = [o for o in option_texts if o.strip().lower() not in ("", "select an option", "select", "--", "please select")]
        if not usable:
            usable = option_texts

        # Yes/No type questions
        for desire in ["yes"]:
            for o in usable:
                if o.strip().lower() == desire:
                    if any(k in l for k in ["willing", "authorized", "eligible", "english", "relocate", "comfortable", "available"]):
                        return o
        # Pick option that matches a profile keyword
        if "experience" in l or "year" in l:
            for o in usable:
                if "4" in o or "3-5" in o or "3 - 5" in o:
                    return o
        return usable[0]

    def _fill_visible_form_fields(self, resume_path: str) -> bool:
        """Fill all visible form fields in the Easy Apply modal. Returns True if anything was filled."""
        filled_any = False
        modal = None
        try:
            modal = self.driver.find_element(By.CSS_SELECTOR, "div.jobs-easy-apply-modal, div[role='dialog']")
        except NoSuchElementException:
            modal = self.driver

        # 1) Resume upload (if upload input is required)
        try:
            file_inputs = modal.find_elements(By.CSS_SELECTOR, "input[type='file']")
            for fi in file_inputs:
                try:
                    if not fi.get_attribute("value"):
                        fi.send_keys(os.path.abspath(resume_path))
                        time.sleep(2)
                        filled_any = True
                except Exception:
                    continue
        except Exception:
            pass

        # 2) Group form questions by their label container
        try:
            groups = modal.find_elements(
                By.CSS_SELECTOR,
                "div.jobs-easy-apply-form-section__grouping, "
                "div.fb-dash-form-element, "
                "div[data-test-form-element]"
            )
        except Exception:
            groups = []

        for grp in groups:
            try:
                label_text = ""
                try:
                    label_el = grp.find_element(By.CSS_SELECTOR, "label, legend, span.artdeco-text-input--label")
                    label_text = (label_el.text or "").strip()
                except NoSuchElementException:
                    pass

                # Text input / number input
                try:
                    inp = grp.find_element(By.CSS_SELECTOR, "input[type='text'], input[type='tel'], input[type='number'], input[type='email']")
                    current = inp.get_attribute("value") or ""
                    if not current.strip():
                        val = self._profile_value_for_label(label_text)
                        if val and self._type_into(inp, val):
                            filled_any = True
                    continue
                except NoSuchElementException:
                    pass

                # Textarea
                try:
                    ta = grp.find_element(By.TAG_NAME, "textarea")
                    if not (ta.get_attribute("value") or "").strip():
                        val = self._profile_value_for_label(label_text)
                        if val and self._type_into(ta, val):
                            filled_any = True
                    continue
                except NoSuchElementException:
                    pass

                # Select dropdown
                try:
                    sel = grp.find_element(By.TAG_NAME, "select")
                    from selenium.webdriver.support.ui import Select
                    s = Select(sel)
                    options = [o.text.strip() for o in s.options]
                    chosen = self._select_best_option(label_text, options)
                    if chosen:
                        try:
                            s.select_by_visible_text(chosen)
                            filled_any = True
                        except Exception:
                            pass
                    continue
                except NoSuchElementException:
                    pass

                # Radio buttons
                try:
                    radios = grp.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    if radios:
                        # Build label texts for each radio
                        radio_pairs = []
                        for r in radios:
                            text = ""
                            try:
                                lid = r.get_attribute("id")
                                if lid:
                                    lab = grp.find_element(By.CSS_SELECTOR, f"label[for='{lid}']")
                                    text = lab.text.strip()
                            except Exception:
                                text = (r.get_attribute("value") or "").strip()
                            radio_pairs.append((text, r))
                        chosen = self._select_best_option(label_text, [t for t, _ in radio_pairs])
                        for text, r in radio_pairs:
                            if text == chosen:
                                try:
                                    self.driver.execute_script("arguments[0].click();", r)
                                    filled_any = True
                                except Exception:
                                    pass
                                break
                    continue
                except NoSuchElementException:
                    pass

                # Checkboxes (typically agreements) - tick required ones
                try:
                    checks = grp.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                    for c in checks:
                        try:
                            if not c.is_selected() and (c.get_attribute("required") or "agree" in label_text.lower()):
                                self.driver.execute_script("arguments[0].click();", c)
                                filled_any = True
                        except Exception:
                            continue
                except NoSuchElementException:
                    pass
            except Exception:
                continue

        return filled_any

    def _handle_easy_apply_modal(self, job: dict, resume_path: str) -> dict:
        """Walk the LinkedIn Easy Apply multi-step modal: fill → next → review → submit."""
        max_steps = 15
        # Stash years for label mapping
        try:
            self._profile_years = job.get("_experience_years")
        except Exception:
            self._profile_years = None

        for step in range(max_steps):
            time.sleep(1.2)

            # Fill any visible questions on this step
            self._fill_visible_form_fields(resume_path)

            # Submit button (final step)
            try:
                submit_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Submit application'], button[aria-label*='Submit application']",
                )
                try:
                    submit_btn.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                time.sleep(3)
                # Close the post-apply confirmation modal if present
                self._close_post_apply_modal()
                logger.info(f"[LinkedIn] Successfully applied to: {job.get('title', '')} at {job.get('company', '')}")
                return {"status": "applied", "message": "Successfully applied via Easy Apply"}
            except NoSuchElementException:
                pass

            # Review button
            try:
                review_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Review your application'], button[aria-label*='Review']",
                )
                try:
                    review_btn.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", review_btn)
                time.sleep(1.5)
                continue
            except NoSuchElementException:
                pass

            # Next/Continue button
            try:
                next_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Continue to next step'], "
                    "button[data-easy-apply-next-button], "
                    "button[aria-label*='Continue']",
                )
                try:
                    next_btn.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(1.5)
                continue
            except NoSuchElementException:
                pass

            # If we got here, we couldn't progress this step
            logger.warning(f"[LinkedIn] Could not progress Easy Apply step {step+1}")
            break

        # Could not finish - close form
        self._close_modal()
        return {
            "status": "manual_needed",
            "message": f"Complex Easy Apply form. URL: {job['url']}",
        }

    def _close_post_apply_modal(self):
        """Close the 'Application sent' confirmation dialog after a successful submit."""
        try:
            done_btn = self.driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label='Done'], button[aria-label='Dismiss']"
            )
            done_btn.click()
            time.sleep(1)
        except NoSuchElementException:
            pass

    def _close_modal(self):
        """Close the Easy Apply modal and discard."""
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
