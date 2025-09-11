import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import time


def create_session(retries: int = 3, backoff_factor: float = 0.5, status_forcelist=None) -> requests.Session:
    """Create a requests Session with retry logic."""
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def post_with_retry(client, message: str, max_retries: int = 3, backoff_factor: float = 2.0) -> bool:
    """Post a message to X with retry logic."""
    for attempt in range(1, max_retries + 1):
        try:
            client.create_tweet(text=message)
            logging.info("Successfully posted to X")
            return True
        except Exception as e:
            logging.error(f"Attempt {attempt} to post failed: {e}")
            if attempt < max_retries:
                sleep_time = backoff_factor ** (attempt - 1)
                logging.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
    logging.error("All attempts to post to X failed")
    return False
