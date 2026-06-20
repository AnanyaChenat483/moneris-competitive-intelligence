"""Google News RSS client for tracking competitor news."""

import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

from config import (
    HIGH_VALUE_NEWS_SOURCES,
    NEWS_MAX_ARTICLES_PER_COMPETITOR,
    NEWS_QUERY_TEMPLATE,
    NEWS_RSS_URL,
    REQUEST_TIMEOUT,
    USER_AGENT,
)


class NewsError(Exception):
    """Raised when the Google News RSS feed cannot be fetched or parsed."""


def _source_weight(source_name: str) -> str:
    lowered = (source_name or "").lower()
    if any(high_value in lowered for high_value in HIGH_VALUE_NEWS_SOURCES):
        return "high"
    return "low"


def _normalize_title(title: str) -> str:
    """Normalize a headline for deduplication (strip trailing ' - Source')."""
    title = re.sub(r"\s*-\s*[^-]+$", "", title or "").strip().lower()
    return re.sub(r"\s+", " ", title)


def fetch_news_for_competitor(competitor: str) -> list[dict]:
    """Fetch and parse Google News RSS results for a competitor.

    Returns a deduplicated, source-weighted list of articles, each with:
    headline, source, url, published_at, source_weight.
    """
    query = NEWS_QUERY_TEMPLATE.format(competitor=competitor)
    url = f"{NEWS_RSS_URL}?q={quote(query)}&hl=en-CA&gl=CA&ceid=CA:en"

    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise NewsError(f"Failed to fetch news for {competitor}: {exc}") from exc

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise NewsError(f"Failed to parse news RSS for {competitor}: {exc}") from exc

    articles = []
    seen_titles = set()

    for item in root.findall("./channel/item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pubdate_el = item.find("pubDate")
        source_el = item.find("source")

        title = (title_el.text or "").strip() if title_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        published_at = (pubdate_el.text or "").strip() if pubdate_el is not None else ""
        source_name = (source_el.text or "").strip() if source_el is not None else ""

        if not title or not link:
            continue

        normalized = _normalize_title(title)
        if normalized in seen_titles:
            continue
        seen_titles.add(normalized)

        if not source_name:
            # Fall back to parsing "Headline - Source Name"
            match = re.search(r"-\s*([^-]+)$", title)
            source_name = match.group(1).strip() if match else "Unknown"

        articles.append({
            "headline": title,
            "source": source_name,
            "url": link,
            "published_at": published_at,
            "source_weight": _source_weight(source_name),
        })

        if len(articles) >= NEWS_MAX_ARTICLES_PER_COMPETITOR:
            break

    return articles
