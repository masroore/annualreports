# Copyright 2023 Dr. Masroor Ehsan
import orjson as json

from src import companies
from scraper_kit.src import utils

if __name__ == "__main__":
    companies = companies.get_companies_list()
    utils.fputb("companies-list.json", json.dumps(companies, option=json.OPT_INDENT_2))
