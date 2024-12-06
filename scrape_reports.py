from pathlib import Path

from src import companies, fetch
import orjson as json

STORAGE_PATH = Path("./storage")
COMPANY_STORAGE_PATH = STORAGE_PATH / "companies"

_COMPANIES = {}


def load_companies_list():
    global _COMPANIES
    _COMPANIES = companies.get_companies_list()


def scrape_company(slug: str):
    print(comp.slug)
    url = companies.BASE_URL + "/Company/" + slug
    content = fetch.http_get(url)
    data = companies.scrape_company_page(content, slug)
    with (COMPANY_STORAGE_PATH / (slug + ".json")).open("wb") as fp:
        fp.write(json.dumps(data, option=json.OPT_INDENT_2))
    return data


if __name__ == "__main__":
    fetch.init_all()
    fetch.http_use_firefox_cookies()
    load_companies_list()
    for comp in _COMPANIES:
        data = scrape_company(comp.slug)
