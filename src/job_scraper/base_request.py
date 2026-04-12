"""
Base Request Scraper - For job sites that don't need browser automation.
Uses requests + BeautifulSoup (faster, lighter than Selenium).
"""

import logging
import time
import re
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BaseRequestScraper(ABC):
    """Base class for HTTP request-based scrapers (no browser needed)."""

    PLATFORM_NAME = "base_request"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _get(self, url: str, params: dict = None, wait: float = 2.0) -> BeautifulSoup:
        """Make GET request and return parsed HTML."""
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            time.sleep(wait)  # Rate limit
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Request failed for {url}: {e}")
            return None

    def _get_json(self, url: str, params: dict = None, wait: float = 2.0) -> dict:
        """Make GET request and return JSON."""
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            time.sleep(wait)
            return resp.json()
        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] JSON request failed: {e}")
            return None

    def login(self, email: str, password: str) -> bool:
        """Most request-based scrapers don't need login."""
        return True

    def stop(self):
        """Close the session."""
        self.session.close()

    @abstractmethod
    def search_jobs(self, title: str, location: str) -> list:
        pass

    def apply_to_job(self, job: dict, resume_path: str) -> dict:
        """Request-based scrapers can't auto-apply; mark as manual."""
        return {
            "status": "manual_needed",
            "message": f"Apply on {self.PLATFORM_NAME}: {job.get('url', '')}",
        }
