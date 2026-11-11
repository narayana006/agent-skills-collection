import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, Timeout


def fetch(url):
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=3))
    try:
        return session.get(url, timeout=5).json()
    except (ConnectionError, Timeout):
        return None
