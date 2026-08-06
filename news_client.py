"""Google News RSS client for tracking competitor news."""

import re
import xml.etree.ElementTree as ET
from collections import Counter
from difflib import SequenceMatcher
from urllib.parse import quote

import requests

from config import (
    COMPETITOR_NEWS_QUERIES,
    HIGH_VALUE_NEWS_SOURCES,
    NEWS_DEDUP_SEMANTIC_THRESHOLD,
    NEWS_DEDUP_SEQUENCE_THRESHOLD,
    NEWS_MAX_ARTICLES_PER_COMPETITOR,
    NEWS_MAX_ARTICLES_PER_COMPETITOR_PER_SCAN,
    NEWS_QUERY_TEMPLATE,
    NEWS_RSS_URL,
    NEWS_SOURCE_CREDIBILITY_RANK,
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


def _source_credibility_rank(source_name: str) -> int:
    """Lower = more credible. Sources not in NEWS_SOURCE_CREDIBILITY_RANK rank last."""
    lowered = (source_name or "").lower()
    for i, name in enumerate(NEWS_SOURCE_CREDIBILITY_RANK):
        if name in lowered:
            return i
    return len(NEWS_SOURCE_CREDIBILITY_RANK)


def _normalize_title(title: str) -> str:
    """Normalize a headline for deduplication (strip trailing ' - Source')."""
    title = re.sub(r"\s*-\s*[^-]+$", "", title or "").strip().lower()
    return re.sub(r"\s+", " ", title)


_DEDUP_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "as", "at", "by",
    "for", "from", "in", "into", "of", "on", "onto", "to", "with", "within",
    "is", "are", "was", "were", "be", "been", "being", "this", "that", "these",
    "those", "it", "its", "their", "they", "which", "while", "over", "under",
    "new", "now", "also",
}


def _semantic_tokens(text: str) -> Counter:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return Counter(w for w in words if w not in _DEDUP_STOPWORDS and len(w) > 2)


def _cosine_similarity(a: Counter, b: Counter) -> float:
    common = set(a) & set(b)
    dot = sum(a[w] * b[w] for w in common)
    mag_a = sum(v * v for v in a.values()) ** 0.5
    mag_b = sum(v * v for v in b.values()) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def headlines_match(headline_a: str, headline_b: str) -> bool:
    """True if two headlines (raw, with trailing ' - Source' still attached) are
    about the same underlying story — by literal text or by meaning, not just
    exact match. Catches syndicated copies of the same story republished with
    slightly different wording across sources, without merging genuinely
    distinct articles that merely share topical words (see the threshold
    tuning notes on NEWS_DEDUP_SEQUENCE_THRESHOLD / _SEMANTIC_THRESHOLD).
    """
    norm_a = _normalize_title(headline_a)
    norm_b = _normalize_title(headline_b)
    seq_ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
    if seq_ratio >= NEWS_DEDUP_SEQUENCE_THRESHOLD:
        return True
    sem_ratio = _cosine_similarity(_semantic_tokens(norm_a), _semantic_tokens(norm_b))
    return sem_ratio >= NEWS_DEDUP_SEMANTIC_THRESHOLD


def dedupe_articles_by_story(articles: list[dict], max_articles: int = None) -> list[dict]:
    """Group articles reporting the same underlying story and keep only the
    single highest-credibility source per group (per NEWS_SOURCE_CREDIBILITY_RANK).

    Unlike a plain "seen URL" or "exact title" check, this groups by fuzzy
    headline similarity so the same story syndicated across several outlets
    with slightly different wording is still caught as one story. Grouping
    is scoped to whatever list is passed in — callers must pre-filter to a
    single competitor, since two different competitors' articles should
    never be merged into one group. Optionally caps the result to
    max_articles, keeping the highest-relevance groups first when
    relevance_to_moneris is present (post-classification reuse), otherwise
    preserving the input order (pre-classification, Google News' own
    relevance ordering).
    """
    groups: list[list[dict]] = []
    for article in articles:
        placed = False
        for group in groups:
            if headlines_match(article.get("headline", ""), group[0].get("headline", "")):
                group.append(article)
                placed = True
                break
        if not placed:
            groups.append([article])

    deduped = [
        min(group, key=lambda a: _source_credibility_rank(a.get("source", "")))
        for group in groups
    ]

    if max_articles is not None:
        if any("relevance_to_moneris" in a for a in deduped):
            deduped.sort(key=lambda a: a.get("relevance_to_moneris", 0), reverse=True)
        deduped = deduped[:max_articles]

    return deduped


def fetch_news_for_competitor(competitor: str) -> list[dict]:
    """Fetch, deduplicate, and cap Google News RSS results for a competitor.

    Collects up to NEWS_MAX_ARTICLES_PER_COMPETITOR raw candidates, groups
    them by fuzzy story similarity (not just exact URL/title match — see
    dedupe_articles_by_story), keeps only the highest-credibility source per
    story, and returns at most NEWS_MAX_ARTICLES_PER_COMPETITOR_PER_SCAN of
    them. This is the single per-scan cap: whatever this returns is what
    gets classified, used for threat scoring, and inserted to Supabase.

    Returns a list of dicts, each with: headline, source, url, published_at,
    source_weight.
    """
    query = COMPETITOR_NEWS_QUERIES.get(competitor, NEWS_QUERY_TEMPLATE.format(competitor=competitor))
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

    candidates = []
    seen_urls = set()

    for item in root.findall("./channel/item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pubdate_el = item.find("pubDate")
        source_el = item.find("source")

        title = (title_el.text or "").strip() if title_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        published_at = (pubdate_el.text or "").strip() if pubdate_el is not None else ""
        source_name = (source_el.text or "").strip() if source_el is not None else ""

        if not title or not link or link in seen_urls:
            continue
        seen_urls.add(link)

        if not source_name:
            # Fall back to parsing "Headline - Source Name"
            match = re.search(r"-\s*([^-]+)$", title)
            source_name = match.group(1).strip() if match else "Unknown"

        candidates.append({
            "headline": title,
            "source": source_name,
            "url": link,
            "published_at": published_at,
            "source_weight": _source_weight(source_name),
        })

        if len(candidates) >= NEWS_MAX_ARTICLES_PER_COMPETITOR:
            break

    return dedupe_articles_by_story(candidates, max_articles=NEWS_MAX_ARTICLES_PER_COMPETITOR_PER_SCAN)
