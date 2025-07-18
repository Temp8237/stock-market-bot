import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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
