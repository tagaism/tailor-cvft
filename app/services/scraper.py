from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
MIN_USEFUL_CHARS = 400
LINKEDIN_HOSTS = {"linkedin.com", "www.linkedin.com", "lnkd.in"}


@dataclass
class ScrapedJob:
    url: str
    title: str
    company: str
    text: str
    warning: str = ""


def host_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def is_linkedin(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == item or host.endswith("." + item) for item in LINKEDIN_HOSTS)


def _looks_thin(text: str) -> bool:
    return len(re.sub(r"\s+", " ", text).strip()) < MIN_USEFUL_CHARS


def _json_ld_job(soup: BeautifulSoup) -> tuple[str, str, str]:
    title = company = description = ""
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        nodes = payload if isinstance(payload, list) else [payload]
        if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
            nodes = payload["@graph"]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            types = node.get("@type", "")
            type_list = types if isinstance(types, list) else [types]
            if "JobPosting" not in type_list:
                continue
            title = title or str(node.get("title") or "")
            org = node.get("hiringOrganization") or {}
            if isinstance(org, dict):
                company = company or str(org.get("name") or "")
            description = description or str(node.get("description") or "")
    if description:
        description = BeautifulSoup(description, "lxml").get_text("\n", strip=True)
    return title.strip(), company.strip(), description.strip()


def _meta(soup: BeautifulSoup, *keys: str) -> str:
    for key in keys:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
    return ""


def _bs_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n", strip=True)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _title_from_page(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        raw = soup.title.string.strip()
        raw = re.split(r"\s+[|\-–—]\s+", raw)[0].strip()
        return raw
    heading = soup.find(["h1"])
    return heading.get_text(" ", strip=True) if heading else ""


def fetch_job(url: str) -> ScrapedJob:
    url = url.strip()
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=20.0,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text
            final_url = str(response.url)
    except httpx.HTTPStatusError as exc:
        warning = f"The page returned HTTP {exc.response.status_code}."
        if is_linkedin(url):
            warning += " LinkedIn usually blocks unauthenticated scrapes — paste the job text below."
        return ScrapedJob(url=url, title="", company="", text="", warning=warning)
    except httpx.HTTPError as exc:
        warning = f"Could not fetch the URL ({exc.__class__.__name__})."
        if is_linkedin(url):
            warning += " Paste the job description text instead."
        return ScrapedJob(url=url, title="", company="", text="", warning=warning)

    soup = BeautifulSoup(html, "lxml")
    ld_title, ld_company, ld_text = _json_ld_job(soup)
    title = ld_title or _meta(soup, "og:title", "twitter:title") or _title_from_page(soup)
    company = ld_company or _meta(soup, "og:site_name")

    extracted = ""
    try:
        import trafilatura

        extracted = trafilatura.extract(html, url=final_url, include_comments=False) or ""
    except Exception:
        extracted = ""

    text = ld_text or extracted or _bs_text(html)
    warning = ""
    if _looks_thin(text):
        if is_linkedin(final_url) or is_linkedin(url):
            warning = (
                "LinkedIn blocked or truncated the posting. Paste the full job description below "
                "and save — the job is kept either way."
            )
        else:
            warning = (
                "Could not extract a useful job description from this page. "
                "Paste the posting text below."
            )
    return ScrapedJob(
        url=final_url or url,
        title=title[:400],
        company=company[:400],
        text=text.strip(),
        warning=warning,
    )
