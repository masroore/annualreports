from pathlib import Path
import orjson as json
from src import companies, fetch

STORAGE = Path("./storage")

_COMPANIES = {}


def load_companies_list():
    global _COMPANIES
    index_file_path = STORAGE / "companies-list.json"
    with index_file_path.open("r") as fp:
        _COMPANIES = json.loads(fp.read())


if __name__ == "__main__":
    fetch.init_all()
    load_companies_list()
