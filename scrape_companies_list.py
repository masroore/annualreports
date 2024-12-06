# Copyright 2023 Dr. Masroor Ehsan
import json

from scraper_kit.src import utils
from src import companies, fetch

if __name__ == "__main__":
    fetch.init_all()
    companies = companies.get_companies_list()
    utils.fputs("./storage/companies-list.json", json.dumps(companies))
