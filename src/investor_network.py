from itertools import product
from pathlib import Path
from string import ascii_lowercase, digits

import orjson as json
import requests
from furl import furl

BASE_URL = "https://www.investornetwork.com"
COMPANY_API = "https://companyhub.issuerdirect.com/api/company/profile"
COMPANY_SEARCH_API = COMPANY_API + "/search"
STORAGE_PATH = Path("./storage/investor_network")


def search(term: str):
    url = furl(COMPANY_SEARCH_API)
    params = {"per-page": 25, "page": 1, "sort": "name", "param": term}
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Origin": BASE_URL,
        "Referer": BASE_URL,
        "isdrplatform": "103",
        "Authorization": "Bearer XXXanonymousXXX",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    url.query.set(params)
    print(url)
    resp = requests.post(url, headers=headers)
    with (STORAGE_PATH / f"index_{term}.json").open("wb") as fp:
        fp.write(json.dumps(resp.json(), option=json.OPT_INDENT_2))


def get_permutations(repeat: int) -> list[str]:
    perms = list(product(ascii_lowercase, repeat=repeat))
    return ["".join(r) for r in perms]


for c in digits:
    search(c)

for i in range(1, 4):
    for term in get_permutations(i):
        search(term)