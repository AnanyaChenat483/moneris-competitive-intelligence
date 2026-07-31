"""Web scraping and content-extraction logic.

Only the parts of a page that are likely to reflect meaningful competitive
information are extracted: headings, pricing-related text, and feature
lists. This keeps diffs focused and avoids noise from navigation, footers,
ads, and other boilerplate.
"""

import re

import requests
from bs4 import BeautifulSoup

from config import (
    FEATURE_TEXT_MAX_LEN,
    FEATURE_TEXT_MIN_LEN,
    HEADING_TAGS,
    PRICING_KEYWORDS,
    PRICING_TEXT_MAX_LEN,
    REQUEST_TIMEOUT,
    USER_AGENT,
)


class ScrapeError(Exception):
    """Raised when a page cannot be fetched or parsed."""


def fetch_page(url: str) -> str:
    """Fetch the raw HTML for a URL, raising ScrapeError on failure."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ScrapeError(f"Failed to fetch {url}: {exc}") from exc
    return response.text


def _clean_text(text: str) -> str:
    """Collapse whitespace and strip a piece of text."""
    return re.sub(r"\s+", " ", text or "").strip()


def extract_title(soup: BeautifulSoup) -> str:
    """Extract the page title, cleaned."""
    if soup.title and soup.title.string:
        return _clean_text(soup.title.string)
    return ""


def extract_headings(soup: BeautifulSoup) -> list[str]:
    """Extract text from h1/h2/h3 tags, deduplicated and cleaned."""
    headings = []
    seen = set()
    for tag in HEADING_TAGS:
        for el in soup.find_all(tag):
            text = _clean_text(el.get_text())
            if text and text not in seen:
                seen.add(text)
                headings.append(text)
    return headings


def extract_pricing_text(soup: BeautifulSoup) -> list[str]:
    """Extract short text snippets that look like pricing information."""
    pricing = []
    seen = set()
    candidates = soup.find_all(["div", "span", "p", "td", "li", "h1", "h2", "h3", "h4"])
    for el in candidates:
        text = _clean_text(el.get_text())
        if not text or len(text) > PRICING_TEXT_MAX_LEN:
            continue
        lowered = text.lower()
        if any(keyword.lower() in lowered for keyword in PRICING_KEYWORDS):
            if text not in seen:
                seen.add(text)
                pricing.append(text)
    return pricing


def extract_features(soup: BeautifulSoup) -> list[str]:
    """Extract short list-item text that likely describes product features."""
    features = []
    seen = set()
    for el in soup.find_all("li"):
        text = _clean_text(el.get_text())
        if FEATURE_TEXT_MIN_LEN <= len(text) <= FEATURE_TEXT_MAX_LEN and text not in seen:
            seen.add(text)
            features.append(text)
    return features


def scrape_page(url: str) -> dict:
    """Fetch a page and extract the title, headings, pricing text, and features."""
    html = fetch_page(url)
    soup = BeautifulSoup(html, "html.parser")

    title = extract_title(soup)

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return {
        "title": title,
        "headings": extract_headings(soup),
        "pricing": extract_pricing_text(soup),
        "features": extract_features(soup),
    }


_ARTICLE_TITLE_TAGS = ["h1", "h2", "h3", "h4"]
_ARTICLE_TITLE_CLASS_HINTS = re.compile(r"title|headline", re.I)
_BODY_TEXT_MIN_LEN = 20
_BODY_TEXT_MAX_PARAGRAPHS = 60


def extract_article_titles(soup: BeautifulSoup) -> list[str]:
    """Extract likely article/post titles from a changelog, newsroom, or blog listing page.

    Covers two common patterns: a heading nested inside an <article> element,
    and elements whose class name signals a title/headline (e.g. "wd_title",
    "post-title") — the latter catches JS-templated listing pages where the
    title isn't wrapped in a heading tag at all.
    """
    titles = []
    seen = set()

    for article in soup.find_all("article"):
        for tag in _ARTICLE_TITLE_TAGS:
            el = article.find(tag)
            if el:
                text = _clean_text(el.get_text())
                if text and text not in seen:
                    seen.add(text)
                    titles.append(text)
                break

    for el in soup.find_all(class_=_ARTICLE_TITLE_CLASS_HINTS):
        text = _clean_text(el.get_text())
        if text and FEATURE_TEXT_MIN_LEN <= len(text) <= PRICING_TEXT_MAX_LEN and text not in seen:
            seen.add(text)
            titles.append(text)

    return titles


def extract_body_paragraphs(soup: BeautifulSoup) -> list[str]:
    """Extract cleaned paragraph text as supporting context for changelog/newsroom pages."""
    paragraphs = []
    for el in soup.find_all("p")[: _BODY_TEXT_MAX_PARAGRAPHS * 3]:
        text = _clean_text(el.get_text())
        if len(text) >= _BODY_TEXT_MIN_LEN:
            paragraphs.append(text)
        if len(paragraphs) >= _BODY_TEXT_MAX_PARAGRAPHS:
            break
    return paragraphs


def scrape_product_update_page(url: str) -> dict:
    """Fetch a changelog/newsroom/roadmap page and extract headings, article titles, and body text.

    Unlike scrape_page (tuned for pricing/product marketing pages), this
    targets listing-style pages where the signal is in post titles and
    announcement text rather than pricing keywords or feature bullet lists.
    """
    html = fetch_page(url)
    soup = BeautifulSoup(html, "html.parser")

    title = extract_title(soup)

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return {
        "title": title,
        "headings": extract_headings(soup),
        "article_titles": extract_article_titles(soup),
        "body_paragraphs": extract_body_paragraphs(soup),
    }


def product_update_content_to_text(content: dict) -> str:
    """Flatten extracted changelog/newsroom content into a single comparable text blob."""
    parts = []

    parts.append("## TITLE")
    if content.get("title"):
        parts.append(content["title"])

    parts.append("## HEADINGS")
    parts.extend(content.get("headings", []))

    parts.append("## ARTICLE TITLES")
    parts.extend(content.get("article_titles", []))

    parts.append("## BODY TEXT")
    parts.extend(content.get("body_paragraphs", []))

    return "\n".join(parts)


def content_to_text(content: dict) -> str:
    """Flatten extracted content into a single comparable text blob."""
    parts = []

    parts.append("## TITLE")
    if content.get("title"):
        parts.append(content["title"])

    parts.append("## HEADINGS")
    parts.extend(content.get("headings", []))

    parts.append("## PRICING")
    parts.extend(content.get("pricing", []))

    parts.append("## FEATURES")
    parts.extend(content.get("features", []))

    return "\n".join(parts)
