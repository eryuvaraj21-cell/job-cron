"""
Base Job Scraper - Abstract class for all job platform scrapers.
"""

import logging
import time
from abc import ABC, abstractmethod

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for job scrapers."""

    PLATFORM_NAME = "base"

    def __init__(self, headless: bool = True, chrome_binary: str = ""):
        self.headless = headless
        self.chrome_binary = chrome_binary
        self.driver = None

    def _create_driver(self) -> webdriver.Chrome:
        """Create a Chrome WebDriver instance."""
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if self.chrome_binary:
            options.binary_location = self.chrome_binary

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )

        return driver

    def start(self):
        """Start the browser."""
        if not self.driver:
            self.driver = self._create_driver()
            logger.info(f"[{self.PLATFORM_NAME}] Browser started")

    def stop(self):
        """Stop the browser."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
            logger.info(f"[{self.PLATFORM_NAME}] Browser stopped")

    def _safe_get(self, url: str, wait_seconds: int = 3):
        """Navigate to URL with rate limiting."""
        self.driver.get(url)
        time.sleep(wait_seconds)

    def _wait_for_element(self, by, value, timeout=15):
        """Wait for an element to be present."""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def _wait_for_clickable(self, by, value, timeout=15):
        """Wait for element to be clickable."""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

    def _scroll_down(self, times: int = 3, pause: float = 1.5):
        """Scroll down the page to load more content."""
        for _ in range(times):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)

    @abstractmethod
    def login(self, email: str, password: str) -> bool:
        """Login to the platform. Returns True on success."""
        pass

    @abstractmethod
    def search_jobs(self, title: str, location: str) -> list:
        """Search for jobs. Returns list of job dicts."""
        pass

    @abstractmethod
    def apply_to_job(self, job: dict, resume_path: str) -> dict:
        """
        Apply to a single job.
        Returns dict: {"status": "applied"|"manual_needed"|"failed", "message": str}
        """
        pass
