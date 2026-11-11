import requests


def is_up(url):
    return requests.head(url, timeout=2).ok
