"""Social channel signal collection: LinkedIn (via Google News proxy) and YouTube RSS.

LinkedIn has no public RSS feed for company pages and gates the post feed
behind login for unauthenticated requests — only the "About" overview page
is reachable. Google News scoped to site:linkedin.com/posts is used as a
proxy signal instead: real and accessible, though noisier than a direct
feed (personal employee posts mention competitors alongside official
company content). analyze_social_intelligence is expected to filter for
official/campaign-relevant signal from this raw set.

YouTube has a real public RSS feed, but only when queried by channel_id —
the legacy ?user= shortcut is unsafe (it can silently resolve to an
unrelated old channel that happens to share the username).
"""

import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

from config import NEWS_RSS_URL, REQUEST_TIMEOUT, USER_AGENT

_YOUTUBE_FEED_URL = "https://www.youtube.com/feeds/videos.xml"
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_MEDIA_NS = {"media": "http://search.yahoo.com/mrss/"}

_LINKEDIN_MAX_RESULTS = 10
_YOUTUBE_MAX_RESULTS = 5
_YOUTUBE_DESCRIPTION_MAX_LEN = 200


class SocialFetchError(Exception):
    """Raised when a social signal source cannot be fetched or parsed."""


def fetch_linkedin_signal(competitor: str, linkedin_query: str) -> list[dict]:
    """Fetch recent LinkedIn-related mentions for a competitor via Google News RSS.

    Returns a list of {headline, source, url, published_at} dicts — the raw
    signal Claude uses to infer messaging theme, campaign focus, etc. Not a
    direct feed of the competitor's own posts (LinkedIn doesn't expose one);
    treat this as noisy proxy signal, not verified first-party content.
    """
    query = f"{linkedin_query} site:linkedin.com/posts"
    url = f"{NEWS_RSS_URL}?q={quote(query)}&hl=en-CA&gl=CA&ceid=CA:en"

    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SocialFetchError(f"Failed to fetch LinkedIn signal for {competitor}: {exc}") from exc

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise SocialFetchError(f"Failed to parse LinkedIn signal RSS for {competitor}: {exc}") from exc

    results = []
    for item in root.findall("./channel/item")[:_LINKEDIN_MAX_RESULTS]:
        title_el = item.find("title")
        link_el = item.find("link")
        pubdate_el = item.find("pubDate")

        title = (title_el.text or "").strip() if title_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        published_at = (pubdate_el.text or "").strip() if pubdate_el is not None else ""

        if not title or not link:
            continue

        results.append({"headline": title, "url": link, "published_at": published_at})

    return results


def resolve_youtube_channel_id(handle: str) -> str:
    """Resolve a YouTube @handle to its canonical channel_id.

    Never trust the legacy ?user= RSS shortcut directly — it can silently
    match an unrelated old channel. This resolves via the @handle page's
    canonical link, which points at the real /channel/UC... URL.
    """
    handle = handle.lstrip("@")
    url = f"https://www.youtube.com/@{handle}"
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SocialFetchError(f"Failed to resolve YouTube handle @{handle}: {exc}") from exc

    match = re.search(r'<link rel="canonical" href="([^"]+)"', response.text)
    if not match:
        raise SocialFetchError(f"Could not find canonical channel link for @{handle}")

    channel_id = match.group(1).rsplit("/", 1)[-1]
    if not channel_id.startswith("UC"):
        raise SocialFetchError(f"Unexpected canonical URL for @{handle}: {match.group(1)}")

    return channel_id


def fetch_youtube_uploads(competitor: str, channel_id: str) -> list[dict]:
    """Fetch recent uploads for a YouTube channel via its public RSS feed.

    Returns a list of {video_id, title, url, published_at, thumbnail_url,
    description} dicts, most recent first. thumbnail_url and description
    come from the feed's <media:group> element (the real YouTube-hosted
    thumbnail, not a placeholder); description is truncated to a short
    snippet. Some channels' feeds return 404/500 despite a correct
    channel_id (a YouTube-side quirk, not a bug here) — callers should
    treat SocialFetchError as "no videos available this scan," not fatal.
    """
    url = f"{_YOUTUBE_FEED_URL}?channel_id={channel_id}"
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SocialFetchError(f"Failed to fetch YouTube feed for {competitor}: {exc}") from exc

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise SocialFetchError(f"Failed to parse YouTube feed for {competitor}: {exc}") from exc

    results = []
    for entry in root.findall("atom:entry", _ATOM_NS)[:_YOUTUBE_MAX_RESULTS]:
        video_id_el = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId")
        title_el = entry.find("atom:title", _ATOM_NS)
        link_el = entry.find("atom:link", _ATOM_NS)
        published_el = entry.find("atom:published", _ATOM_NS)
        media_group_el = entry.find("media:group", _MEDIA_NS)

        video_id = (video_id_el.text or "").strip() if video_id_el is not None else ""
        title = (title_el.text or "").strip() if title_el is not None else ""
        link = link_el.get("href", "") if link_el is not None else ""
        published_at = (published_el.text or "").strip() if published_el is not None else ""

        thumbnail_url = ""
        description = ""
        if media_group_el is not None:
            thumb_el = media_group_el.find("media:thumbnail", _MEDIA_NS)
            desc_el = media_group_el.find("media:description", _MEDIA_NS)
            if thumb_el is not None:
                thumbnail_url = thumb_el.get("url", "")
            if desc_el is not None and desc_el.text:
                description = desc_el.text.strip().replace("\n", " ")
                if len(description) > _YOUTUBE_DESCRIPTION_MAX_LEN:
                    description = description[:_YOUTUBE_DESCRIPTION_MAX_LEN].rsplit(" ", 1)[0] + "…"

        if not title:
            continue

        results.append({
            "video_id": video_id,
            "title": title,
            "url": link,
            "published_at": published_at,
            "thumbnail_url": thumbnail_url,
            "description": description,
        })

    return results
