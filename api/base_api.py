"""
api/base_api.py
================
Base class for all API clients.

WHY RETRY LOGIC?
    Networks are unreliable. A request that fails once
    often succeeds on the second attempt.
    Without retry logic, a single blip crashes the app.

WHY TIMEOUTS?
    Without a timeout, a slow API can freeze your entire
    application indefinitely. Always set a timeout.

WHY EXPONENTIAL BACKOFF?
    If an API is struggling, hammering it with retries
    makes it worse. Exponential backoff waits longer
    between each retry:
        Attempt 1 — wait 1 second
        Attempt 2 — wait 2 seconds
        Attempt 3 — wait 4 seconds
    This gives the API time to recover.
"""

import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class BaseAPI:
    """
    Parent class for all API clients.
    Provides shared HTTP request logic with retries and timeouts.
    """

    BASE_URL    = ""      # Override in each subclass
    MAX_RETRIES = 3       # How many times to retry a failed request
    TIMEOUT     = 10      # Seconds before giving up on a request
    RETRY_DELAY = 1       # Starting delay between retries in seconds

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.session = requests.Session()

        # Set default headers for all requests from this client
        self.session.headers.update({
            'User-Agent': 'StockAnalyzer/1.0',
            'Accept':     'application/json',
        })

    def _get(self, url: str, params: dict = None) -> Optional[dict]:
        """
        Makes a GET request with automatic retry and backoff.

        Args:
            url:    Full URL to request
            params: Query parameters dict

        Returns:
            Parsed JSON as dict, or None if all retries fail
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.debug(f"GET {url} (attempt {attempt})")

                response = self.session.get(
                    url,
                    params  = params,
                    timeout = self.TIMEOUT,
                )

                # Raise an exception for 4xx and 5xx status codes
                response.raise_for_status()

                logger.debug(f"Response {response.status_code} from {url}")
                return response.json()

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt} for {url}")

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else 0

                # 429 = rate limited — wait longer before retrying
                if status == 429:
                    wait = self.RETRY_DELAY * (2 ** attempt) * 5
                    logger.warning(f"Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue

                # 401/403 = auth error — retrying won't help
                if status in (401, 403):
                    logger.error(f"Authentication failed for {url}: {e}")
                    return None

                logger.warning(f"HTTP {status} on attempt {attempt}: {e}")

            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error on attempt {attempt} for {url}")

            except ValueError as e:
                logger.error(f"Failed to parse JSON from {url}: {e}")
                return None

            # Exponential backoff before next retry
            if attempt < self.MAX_RETRIES:
                wait = self.RETRY_DELAY * (2 ** (attempt - 1))
                logger.debug(f"Waiting {wait}s before retry...")
                time.sleep(wait)

        logger.error(f"All {self.MAX_RETRIES} attempts failed for {url}")
        return None

    def is_available(self) -> bool:
        """
        Quick check if the API is reachable.
        Useful for the settings screen to show API status.
        """
        raise NotImplementedError("Subclasses must implement is_available()")
