# Copyright 2023 Dr. Masroor Ehsan
import orjson as json

from scraper_kit.src import utils
from src import companies, fetch

if __name__ == "__main__":
    fetch.init_all()
    fetch.http_use_firefox_cookies()
    companies = companies.get_companies_list()
    utils.fputb("./storage/companies.json", json.dumps(companies))
