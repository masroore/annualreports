from pathlib import Path

from src import scraper, fetch
import orjson as json

STORAGE_PATH = Path("./storage")
COMPANY_STORAGE_PATH = STORAGE_PATH / "companies"

_AR_COMPANIES = {}
_RR_COMPANIES = {}


def load_companies_list():
    global _AR_COMPANIES, _RR_COMPANIES
    _AR_COMPANIES = scraper.get_companies_list(False)
    with (STORAGE_PATH / "companies-ar.json").open("wb") as fp:
        fp.write(json.dumps(_AR_COMPANIES, option=json.OPT_INDENT_2))
    _RR_COMPANIES = scraper.get_companies_list(True)
    with (STORAGE_PATH / "companies-rr.json").open("wb") as fp:
        fp.write(json.dumps(_RR_COMPANIES, option=json.OPT_INDENT_2))


def fname_from_slug(slug: str, is_csr: bool) -> str:
    pfx = "rr" if is_csr else "ar"
    return f"{slug.lower()}-{pfx}.json"


def scrape_company(slug: str, ix: int, total: int, is_csr: bool):
    print(f"[{ix:04d}/{total}] {slug}")
    url = scraper.get_url(is_csr, "/Company/" + slug)
    content = fetch.http_get(url)
    data = scraper.scrape_company_page(content, slug, is_csr)
    with (COMPANY_STORAGE_PATH / fname_from_slug(slug, is_csr)).open("wb") as fp:
        fp.write(json.dumps(data, option=json.OPT_INDENT_2))
    return data


if __name__ == "__main__":
    fetch.init_all()
    fetch.http_use_firefox_cookies()
    load_companies_list()

    total = len(_AR_COMPANIES)
    for ix, comp in enumerate(_AR_COMPANIES):
        data = scrape_company(comp.slug, ix + 1, total, False)

    total = len(_RR_COMPANIES)
    for ix, comp in enumerate(_RR_COMPANIES):
        data = scrape_company(comp.slug, ix + 1, total, True)
