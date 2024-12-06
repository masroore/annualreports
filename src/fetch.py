import json
import os
import pickle
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import browser_cookie3
import furl
from curl_cffi import requests
from stash import StashOptions, get_leveldb_lzma_stash
from stash.consts import SECONDS_IN_DAY

_cache = None
_cookies = None
_session = requests.session.Session()
_thread_workers_count = 4

STORAGE_PATH = Path("./storage")
CACHE_PATH = Path("./__cache__")


def __init_cache():
    global _cache
    options = StashOptions()
    options.fs_cache_dir = str(CACHE_PATH.absolute())
    # options.lmdb_map_size = SIZE_MB * int(config("cache.lmdb_map_size", 64))
    options.cache_min_size = 300
    options.cache_max_age = 3 * SECONDS_IN_DAY
    _cache = get_leveldb_lzma_stash(options)


def http_use_firefox_cookies():
    global _cookies
    _cookies = browser_cookie3.firefox()


def __init_transport():
    global _session
    _session.verify = False


_cookie_file = STORAGE_PATH / "cookies.pkl"


def _cookies_save():
    global _session
    with _cookie_file.open("wb") as fp:
        pickle.dump(_session.cookies.get_dict(), fp)


def _cookies_load():
    global _session
    if not os.path.isfile(_cookie_file):
        _session.cookies = None

    with _cookie_file.open("rb") as fp:
        _session.cookies = pickle.load(fp)


def http_set_referer(s: str):
    global _session
    u = furl.furl(s.lower())
    _session.headers.update(
        {
            "Referer": s,
            "Host": u.host,
        }
    )


def init_all():
    __init_cache()
    __init_transport()


def http_post(url: str, data):
    return _session.post(url=url, data=data, allow_redirects=True, impersonate="chrome")


def _http_fetch(url: str, is_json: bool = False, save_cookies: bool = False) -> tuple[str, Any]:
    if _cookies:
        response = _session.get(url=url, cookies=_cookies, impersonate="chrome")
    else:
        response = _session.get(url=url, impersonate="chrome")

    if response.status_code != 200:
        return response.url, None

    if save_cookies:
        _cookies_save()

    if is_json:
        return response.url, response.json()

    return response.url, response.text


def http_set_header(header: str, value: str):
    _session.headers.update({header: value})


def cache_rm(key: str) -> bool:
    if _cache.exists(key):
        _cache.rm(key)
        return True
    return False


def cache_put(key: str, content) -> bool:
    _cache.write(key, content)
    return True


def cache_get(key: str) -> str | None:
    if _cache.exists(key):
        return _cache.read(key)
    return None


def ip_info() -> tuple[str, dict]:
    http_set_referer("https://ipinfo.io/json")
    return _http_fetch("https://ipinfo.io/json", True)


def http_get(
    url: str,
    bypass_cache: bool = False,
    is_json: bool = False,
    save_cookies: bool = False,
):
    if not bypass_cache and _cache.exists(url):
        return _cache.read(url)

    the_url, content = _http_fetch(url, is_json, save_cookies)

    if not bypass_cache and content:
        _cache.write(url, content)

    return content


def http_get_canon_url(url: str, save_cookies: bool = False) -> tuple[str, Any]:
    canon_url, content = _http_fetch(url, False, save_cookies)

    if content:
        _cache.write(canon_url, content)

    return canon_url, content


def json_get(url: str, bypass_cache: bool = False):
    content = http_get(url, bypass_cache)
    if content:
        return json.loads(content)
    return content
    # return json.loads(http_get(url, bypass_cache, True))
    # return json.loads(http_get(url, bypass_cache))


def sanitize_url(url: str) -> str:
    return urljoin(url, urlparse(url).path)


def http_set_proxy(proxy_settings: dict):
    global _session

    host = proxy_settings["host"]
    port = proxy_settings["port"]
    protocol = proxy_settings["protocol"]
    username = proxy_settings["username"]
    password = proxy_settings["password"]

    if password:
        if username:
            proxy_url = f"{protocol}://{username}:{password}@{host}:{port}"
        else:
            proxy_url = f"{protocol}://{password}@{host}:{port}"
    else:
        proxy_url = f"{protocol}://{host}:{port}"

    proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }
    _session.proxies.clear()
    _session.proxies.update(proxies)


def cache_rm_last_page(urls: list[str]):
    for u in reversed(urls):
        if _cache.exists(u):
            _cache.rm(u)
            return


def set_precache_workers(num: int):
    global _thread_workers_count
    _thread_workers_count = num


def _parallel_get(url: str):
    global _session
    return _session.get(url, impersonate="chrome")


def parallel_fetch(urls: list[str]):
    pool = ThreadPoolExecutor(max_workers=_thread_workers_count)
    missing_urls = [u for u in urls if not _cache.exists(u)]
    for response in pool.map(_parallel_get, missing_urls):
        _cache.write(response.request.url, response.text)
