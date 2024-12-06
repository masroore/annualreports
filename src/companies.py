# Copyright 2023 Dr. Masroor Ehsan
from __future__ import annotations

import os.path
import re
from dataclasses import dataclass

import jmespath
import orjson as json
from selectolax.parser import HTMLParser, Node

from . import fetch

_rex_year = re.compile(r"\b(19|20)\d{2}\b")
BASE_URL = "https://www.annualreports.com"


@dataclass
class CompanyIndex:
    name: str
    slug: str
    sector: str | None = None
    industry: str | None = None


@dataclass
class AnnualReport:
    report_id: str
    preview_img: str
    heading: str
    report_year: str
    view_link: str
    download_link: str


def _extract_text(node: Node, selector: str | None = None) -> str | None:
    if selector:
        target = node.css_first(selector)
    else:
        target = node

    text = target.text(strip=True).strip()
    if text:
        return text
    return None


def scrape_companies_list_page(html: str | bytes) -> list[CompanyIndex]:
    companies: list[CompanyIndex] = []
    dom = HTMLParser(html)
    for li in dom.css("li:not(.header_section)"):
        company_name = li.css_first("span.companyName")
        if not company_name:
            continue

        link = company_name.css_first("a").attributes.get("href")
        company = CompanyIndex(name=company_name.text(strip=True).strip(), slug=os.path.basename(link))

        company.sector = _extract_text(li, "span.sectorName")
        company.industry = _extract_text(li, "span.industryName")

        companies.append(company)

    return companies


def get_companies_list(url: str | None = None) -> list[CompanyIndex]:
    if not url:
        url = BASE_URL + "/Companies"

    content = fetch.http_get(url)
    return scrape_companies_list_page(content)


def scrape_company_page(html: str | bytes) -> dict:
    company = {}
    dom = HTMLParser(html)

    script = dom.css_first('script[type="application/ld+json"]')
    if script:
        code = _extract_text(script)
        if '"@type": "Corporation"' in code:
            data = json.loads(code)
            company = jmespath.search(
                """
{
    name: name,
    description: description,
    url: url,
    logo_url: logo.contentUrl,
    social_links: sameAs
}
            """,
                data,
            )

    top_content_list = dom.css_first("li.top_content_list")
    if top_content_list:
        company["ticker_name"] = _extract_text(top_content_list, "span.ticker_name")
        div_right = top_content_list.css_first("div.right")
        if div_right:
            div_right.css_first("span.blue_txt").decompose(recursive=True)
            div_right.css_first("span.more").decompose(recursive=True)
            company["exchange"] = _extract_text(div_right)

    company["sort_char"] = company["ticker_name"][0].lower()
    company["employees"] = _extract_text(dom.root, "li.employees")
    company["location"] = _extract_text(dom.root, "li.location")
    company["reports"]: list[AnnualReport] = []

    most_recent_block = dom.css_first("div.most_recent_content_block")
    if most_recent_block:
        report_id = preview_img = heading = None
        most_recent_pvw_img = most_recent_block.css_first("div.most_recent_pvw_img > img")
        if most_recent_pvw_img:
            preview_img = most_recent_pvw_img.attributes.get("src")
            report_id = os.path.splitext(os.path.basename(preview_img))[0]

        bold_txt = most_recent_block.css_first(".bold_txt")
        if bold_txt:
            heading = _extract_text(bold_txt)
        report_year = _extract_report_year(heading)
        if report_id:
            company["reports"].append(
                AnnualReport(
                    report_id=report_id,
                    report_year=report_year,
                    preview_img=preview_img,
                    heading=heading,
                    view_link="",
                    download_link="",
                )
            )

    reports = _scrape_archived_reports(dom.root)
    if any(reports):
        company["reports"].extend(reports)

    return company


def _extract_report_year(s: str) -> str:
    m = _rex_year.search(s)
    if m:
        return m.group(0)


def _scrape_archived_reports(node: Node) -> list[AnnualReport]:
    reports: list[AnnualReport] = []

    archived_report_content_block = node.css_first("div.archived_report_content_block > ul")
    if not archived_report_content_block:
        return reports

    for li in archived_report_content_block.css("li"):
        preview_img = li.css_first("img").attributes.get("src")
        report_id = os.path.splitext(os.path.basename(preview_img))[0]
        heading = _extract_text(li, "span.heading")
        year = _extract_report_year(heading)
        reports.append(
            AnnualReport(
                report_id=report_id,
                preview_img=preview_img,
                heading=heading,
                report_year=year,
                view_link=(li.css_first("span.view_annual_report > a").attributes.get("href")),
                download_link=(li.css_first("span.download > a").attributes.get("href")),
            )
        )

    return reports
