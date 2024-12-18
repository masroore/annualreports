# Copyright 2023 Dr. Masroor Ehsan
from __future__ import annotations

import os.path
import re
from dataclasses import dataclass

import jmespath
import orjson as json
from selectolax.parser import HTMLParser, Node

from src import fetch

_rex_year = re.compile(r"\b(19|20)\d{2}\b")
AR_BASE_URL = "https://www.annualreports.com"
RR_BASE_URL = "https://www.responsibilityreports.com"


@dataclass
class CompanyIndex:
    name: str
    slug: str
    sector: str | None = None
    industry: str | None = None


@dataclass
class AnnualReport:
    is_csr: bool
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

    if not target:
        return None

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


def get_url(is_csr: bool, path: str | None) -> str | None:
    if not path:
        return None
    if "://" in path:
        return path
    return (RR_BASE_URL if is_csr else AR_BASE_URL) + "/" + path.lstrip("/")


def get_companies_list(is_csr: bool, url: str | None = None) -> list[CompanyIndex]:
    if not url:
        url = get_url(is_csr, "/Companies")

    content = fetch.http_get(url)
    return scrape_companies_list_page(content)


def _zap_node(node: Node | None):
    if node:
        node.decompose(recursive=True)


def _extract_download_key(s: str | None) -> str | None:
    if s:
        s = "_".join(s.split("_")[:-1])
        return "/".join(s.split("/")[-2:])

    return None


def scrape_company_page(html: str | bytes, slug: str, is_csr: bool) -> dict:
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
    rating_count: aggregateRating.reviewCount,
    rating_value: aggregateRating.ratingValue,    
    social_links: sameAs
}
            """,
                data,
            )

    company["slug"] = slug
    top_content_list = dom.css_first("li.top_content_list")
    if top_content_list:
        company["ticker_name"] = _extract_text(top_content_list, "span.ticker_name")
        div_right = top_content_list.css_first("div.right")
        if div_right:
            _zap_node(div_right.css_first("span.blue_txt"))
            _zap_node(div_right.css_first("span.more"))
            company["exchange"] = _extract_text(div_right)

    if company.get("ticker_name"):
        company["sort_char"] = company["ticker_name"][0].lower()
    else:
        company["sort_char"] = company["slug"][0].lower()
    company["employees"] = _extract_text(dom.root, "li.employees")
    company["location"] = _extract_text(dom.root, "li.location")
    if company["location"]:
        company["location"] = company["location"].replace("Based in ", "").strip()
    company["reports"]: list[AnnualReport] = []

    most_recent_block = dom.css_first("div.most_recent_content_block")
    if most_recent_block:
        report_id = preview_img = heading = report_year = None
        most_recent_pvw_img = most_recent_block.css_first("div.most_recent_pvw_img > img")
        if most_recent_pvw_img:
            preview_img = most_recent_pvw_img.attributes.get("src")
            report_id = os.path.splitext(os.path.basename(preview_img))[0]

        bold_txt = most_recent_block.css_first(".bold_txt")
        if bold_txt:
            heading = _extract_text(bold_txt)
            if heading:
                report_year = _extract_report_year(heading)

        company["years"] = []
        if report_year:
            company["years"].append(int(report_year))

        if report_id:
            company["reports"].append(
                AnnualReport(
                    is_csr=is_csr,
                    report_id=report_id,
                    report_year=report_year,
                    preview_img=preview_img,
                    heading=heading,
                    view_link="",
                    download_link="",
                )
            )

    reports = _scrape_archived_reports(dom.root, is_csr)
    if any(reports):
        company["reports"].extend(reports)
        for rep in reports:
            if rep.report_year:
                company["years"].append(int(rep.report_year))

        company["years"] = sorted(company["years"])
        company["report_key"] = _extract_download_key(reports[-1].download_link)

    company = {k: v.strip() if v is str else v for k, v in sorted(company.items())}
    return company


def _extract_report_year(s: str) -> str:
    m = _rex_year.search(s)
    if m:
        return m.group(0)


def _scrape_archived_reports(node: Node, is_csr: bool) -> list[AnnualReport]:
    reports: list[AnnualReport] = []

    archived_report_content_block = node.css_first("div.archived_report_content_block > ul")
    if not archived_report_content_block:
        return reports

    for li in archived_report_content_block.css("li"):
        report_id = preview_img = heading = None

        p_img = li.css_first("img")
        if p_img:
            preview_img = p_img.attributes.get("src")
            report_id = os.path.splitext(os.path.basename(preview_img))[0]

        heading = _extract_text(li, "span.heading")
        year = _extract_report_year(heading)
        view_link = download_link = None
        vw_report = li.css_first("span.view_annual_report > a")
        if vw_report:
            view_link = vw_report.attributes.get("href")
        dl_report = li.css_first("span.download > a")
        if dl_report:
            download_link = dl_report.attributes.get("href")

        reports.append(
            AnnualReport(
                is_csr=is_csr,
                report_id=report_id,
                preview_img=get_url(is_csr, preview_img),
                heading=heading,
                report_year=year,
                view_link=get_url(is_csr, view_link),
                download_link=get_url(is_csr, download_link),
            )
        )

    return reports
