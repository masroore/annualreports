from itertools import product
from pathlib import Path
from string import ascii_lowercase, digits

import orjson as json
import requests
from furl import furl

BASE_URL = "https://www.investornetwork.com"
COMPANY_API = "https://companyhub.issuerdirect.com/api/company/profile"
COMPANY_SEARCH_API = COMPANY_API + "/search"
COMPANY_INFO_API = COMPANY_API + "/info"
STORAGE_PATH = Path("./storage/investor_network")
INFO_STORAGE_PATH = Path("./storage/investor_network/info")


def call_api(url: str):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Origin": BASE_URL,
        "Referer": BASE_URL,
        "isdrplatform": "103",
        "Authorization": "Bearer XXXanonymousXXX",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    try:
        resp = requests.post(url, headers=headers)
        return resp
    except:
        return None


def index_fpath(term: str) -> Path:
    return STORAGE_PATH / f"index_{term.lower()}.json"


def search(term: str):
    url = furl(COMPANY_SEARCH_API)
    params = {"per-page": 25, "page": 1, "sort": "name", "param": term.upper()}
    url.query.set(params)
    print(url)
    resp = call_api(url)
    with index_fpath(term).open("wb") as fp:
        fp.write(json.dumps(resp.json(), option=json.OPT_INDENT_2))


def info(comp_id: str):
    url = furl(COMPANY_INFO_API)
    url.query.set({"id": comp_id, "expand": "securityListings.quote"})
    print(url)
    resp = call_api(url)
    if resp:
        with (INFO_STORAGE_PATH / f"{comp_id.lower()}.json").open("wb") as fp:
            fp.write(json.dumps(resp.json(), option=json.OPT_INDENT_2))


def get_permutations(repeat: int) -> list[str]:
    perms = list(product(ascii_lowercase + digits, repeat=repeat))
    terms = ["".join(r) for r in perms]
    return [x for x in terms if not index_fpath(x).exists()]


for c in digits:
    if not index_fpath(c):
        search(c)

for i in range(1, 5):
    for term in get_permutations(i):
        search(term)
