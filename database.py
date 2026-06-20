"""Supabase (PostgreSQL) persistence layer for the Competitive Intelligence Monitor.

Tables must be created in Supabase before first run — execute schema.sql in the
Supabase SQL Editor (app.supabase.com → SQL Editor).

Credentials are read from environment variables:
  SUPABASE_URL   — project URL, e.g. https://xxxx.supabase.co
  SUPABASE_KEY   — anon or service-role key from Project Settings → API
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_supabase_client: Client = None

# Streamlit Cloud captures stdout — use print(flush=True) so logs appear immediately.
def _log(msg: str) -> None:
    print(f"[DB] {msg}", flush=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        _log(f"Creating Supabase client. URL set: {bool(url)}, KEY set: {bool(key)}")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set. "
                "Add them to .env locally, or to Streamlit Cloud → Settings → Secrets."
            )
        _supabase_client = create_client(url, key)
        _log("Supabase client created successfully.")
    return _supabase_client


def init_db() -> None:
    """Verify Supabase connectivity on startup. Tables are created via schema.sql."""
    _log("init_db: verifying Supabase connectivity...")
    try:
        resp = _client().table("snapshots").select("competitor").limit(1).execute()
        _log(f"init_db: connected. snapshots table reachable ({len(resp.data or [])} row(s) in probe).")
    except Exception as exc:
        _log(f"init_db: ERROR — {exc}")
        raise


# ---------------------------------------------------------------------------
# Snapshots (Layer 1)
# ---------------------------------------------------------------------------

def get_snapshot(competitor: str, page_type: str):
    _log(f"get_snapshot({competitor!r}, {page_type!r})")
    try:
        resp = (
            _client()
            .table("snapshots")
            .select("*")
            .eq("competitor", competitor)
            .eq("page_type", page_type)
            .execute()
        )
        if resp.data:
            row = resp.data[0]
            _log(
                f"  → snapshot found: hash={row.get('content_hash', '')[:12]}… "
                f"text_len={len(row.get('content_text', ''))} updated_at={row.get('updated_at')}"
            )
            return row
        else:
            _log(f"  → no snapshot found (resp.data={resp.data!r})")
            return None
    except Exception as exc:
        _log(f"  ERROR in get_snapshot: {exc}")
        raise


def upsert_snapshot(competitor: str, page_type: str, url: str, page_title: str,
                     content_hash: str, content_text: str) -> None:
    # Truncate to stay well within PostgREST's default 1 MB body limit.
    original_len = len(content_text)
    if len(content_text) > 200_000:
        content_text = content_text[:200_000]
        _log(f"upsert_snapshot: content_text truncated {original_len} → 200000 chars")

    _log(
        f"upsert_snapshot({competitor!r}, {page_type!r}) "
        f"hash={content_hash[:12]}… text_len={len(content_text)}"
    )
    try:
        resp = _client().table("snapshots").upsert(
            {
                "competitor": competitor,
                "page_type": page_type,
                "url": url,
                "page_title": page_title,
                "content_hash": content_hash,
                "content_text": content_text,
                "updated_at": _now(),
            },
            on_conflict="competitor,page_type",
        ).execute()
        _log(f"  → upsert_snapshot done, rows_returned={len(resp.data or [])}")
    except Exception as exc:
        _log(f"  ERROR in upsert_snapshot: {exc}")
        raise


# ---------------------------------------------------------------------------
# Website changes (Layer 1 / Tab 1)
# ---------------------------------------------------------------------------

def insert_website_change(competitor: str, page_type: str, url: str, change_type: str,
                            description: str, customer_impact_score: int,
                            revenue_sensitivity: str, segment_affected: str, diff: str) -> None:
    _log(
        f"insert_website_change({competitor!r}, {page_type!r}) "
        f"type={change_type!r} impact={customer_impact_score}"
    )
    try:
        resp = _client().table("website_changes").insert(
            {
                "detected_at": _now(),
                "competitor": competitor,
                "page_type": page_type,
                "url": url,
                "change_type": change_type,
                "description": description,
                "customer_impact_score": customer_impact_score,
                "revenue_sensitivity": revenue_sensitivity,
                "segment_affected": segment_affected,
                "diff": diff,
            }
        ).execute()
        _log(f"  → insert_website_change done, rows_returned={len(resp.data or [])}")
    except Exception as exc:
        _log(f"  ERROR in insert_website_change: {exc}")
        raise


def get_website_changes(limit: int = 100, competitor: str = None, change_type: str = None):
    _log(f"get_website_changes(limit={limit}, competitor={competitor!r}, change_type={change_type!r})")
    try:
        q = _client().table("website_changes").select("*")
        if competitor and competitor != "All":
            q = q.eq("competitor", competitor)
        if change_type and change_type != "All":
            q = q.eq("change_type", change_type)
        rows = q.order("detected_at", desc=True).order("id", desc=True).limit(limit).execute().data or []
        _log(f"  → get_website_changes returned {len(rows)} row(s)")
        return rows
    except Exception as exc:
        _log(f"  ERROR in get_website_changes: {exc}")
        raise


# ---------------------------------------------------------------------------
# Review sentiment (Layer 2 / Tab 2 — Google Play Store)
# ---------------------------------------------------------------------------

def insert_review_sentiment(competitor: str, sentiment: str, severity_score: float,
                              themes: list, top_complaints: list, top_praise: list,
                              moneris_opportunity: str, source_breakdown: dict,
                              review_count: int) -> None:
    try:
        _client().table("review_sentiment").insert(
            {
                "scanned_at": _now(),
                "competitor": competitor,
                "sentiment": sentiment,
                "severity_score": severity_score,
                "themes": themes,
                "top_complaints": top_complaints,
                "top_praise": top_praise,
                "moneris_opportunity": moneris_opportunity,
                "source_breakdown": source_breakdown,
                "review_count": review_count,
            }
        ).execute()
    except Exception as exc:
        _log(f"ERROR in insert_review_sentiment({competitor!r}): {exc}")
        raise


def get_latest_review_sentiment() -> dict:
    """Return a dict mapping competitor -> latest review sentiment row."""
    resp = _client().table("review_sentiment").select("*").order("id", desc=True).execute()
    result = {}
    for row in (resp.data or []):
        if row["competitor"] not in result:
            result[row["competitor"]] = row
    return result


# ---------------------------------------------------------------------------
# News articles (Layer 3 / Tab 3)
# ---------------------------------------------------------------------------

def insert_news_article(competitor: str, headline: str, source: str, url: str,
                          published_at: str, impact_type: str, relevance_to_moneris: int,
                          market_impact: str, summary: str, source_weight: str) -> None:
    """Insert a news article, skipping duplicates (same competitor + url)."""
    try:
        _client().table("news_articles").upsert(
            {
                "fetched_at": _now(),
                "competitor": competitor,
                "headline": headline,
                "source": source,
                "url": url,
                "published_at": published_at,
                "impact_type": impact_type,
                "relevance_to_moneris": relevance_to_moneris,
                "market_impact": market_impact,
                "summary": summary,
                "source_weight": source_weight,
            },
            on_conflict="competitor,url",
            ignore_duplicates=True,
        ).execute()
    except Exception as exc:
        _log(f"ERROR in insert_news_article({competitor!r}): {exc}")
        raise


def get_news_articles(limit: int = 100, competitor: str = None, impact_type: str = None):
    q = _client().table("news_articles").select("*")
    if competitor and competitor != "All":
        q = q.eq("competitor", competitor)
    if impact_type and impact_type != "All":
        q = q.eq("impact_type", impact_type)
    return (
        q.order("relevance_to_moneris", desc=True)
        .order("fetched_at", desc=True)
        .limit(limit)
        .execute()
        .data or []
    )


# ---------------------------------------------------------------------------
# Threat scores (Feature 2 / Tab 5)
# ---------------------------------------------------------------------------

def insert_threat_score(competitor: str, threat_score: float, review_component: float,
                          news_component: float, feature_velocity_component: float,
                          smb_relevance_component: float, reason: str, scanned_at: str = None) -> None:
    try:
        _client().table("threat_scores").insert(
            {
                "scanned_at": scanned_at or _now(),
                "competitor": competitor,
                "threat_score": threat_score,
                "reddit_component": review_component,  # column name kept for schema compatibility
                "news_component": news_component,
                "feature_velocity_component": feature_velocity_component,
                "smb_relevance_component": smb_relevance_component,
                "reason": reason,
            }
        ).execute()
    except Exception as exc:
        _log(f"ERROR in insert_threat_score({competitor!r}): {exc}")
        raise


def get_threat_score_history(competitor: str = None):
    q = _client().table("threat_scores").select("*")
    if competitor and competitor != "All":
        q = q.eq("competitor", competitor)
    return q.order("scanned_at").order("id").execute().data or []


def get_latest_threat_scores() -> dict:
    """Return a dict mapping competitor -> latest threat_score row."""
    resp = _client().table("threat_scores").select("*").order("id", desc=True).execute()
    result = {}
    for row in (resp.data or []):
        if row["competitor"] not in result:
            result[row["competitor"]] = row
    return result


def get_previous_threat_score(competitor: str):
    """Return the second-most-recent threat_score row for a competitor, or None."""
    resp = (
        _client()
        .table("threat_scores")
        .select("*")
        .eq("competitor", competitor)
        .order("id", desc=True)
        .limit(2)
        .execute()
    )
    rows = resp.data or []
    return rows[1] if len(rows) >= 2 else None


# ---------------------------------------------------------------------------
# Comparison cards (Feature 1 / Tab 4)
# ---------------------------------------------------------------------------

def insert_comparison_card(comparison: dict, top_threats: list, top_advantages: list) -> None:
    try:
        _client().table("comparison_cards").insert(
            {
                "generated_at": _now(),
                "comparison_json": comparison,
                "top_threats": top_threats,
                "top_advantages": top_advantages,
            }
        ).execute()
    except Exception as exc:
        _log(f"ERROR in insert_comparison_card: {exc}")
        raise


def get_latest_comparison_card():
    resp = (
        _client()
        .table("comparison_cards")
        .select("*")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    record = resp.data[0]
    # JSONB columns come back as Python objects — no json.loads needed
    record["comparison"] = record["comparison_json"]
    return record


# ---------------------------------------------------------------------------
# Historical events (Feature 4)
# ---------------------------------------------------------------------------

def insert_historical_event(competitor: str, date: str, event_type: str, description: str,
                              source: str, impact_score: int) -> None:
    try:
        _client().table("historical_events").insert(
            {
                "competitor": competitor,
                "date": date,
                "event_type": event_type,
                "description": description,
                "source": source,
                "impact_score": impact_score,
            }
        ).execute()
    except Exception as exc:
        _log(f"ERROR in insert_historical_event({competitor!r}): {exc}")
        raise


def get_historical_events(competitor: str = None):
    q = _client().table("historical_events").select("*")
    if competitor and competitor != "All":
        q = q.eq("competitor", competitor)
    return q.order("date").execute().data or []


def count_historical_events() -> int:
    resp = _client().table("historical_events").select("id").execute()
    return len(resp.data or [])


# ---------------------------------------------------------------------------
# Scan log
# ---------------------------------------------------------------------------

def start_scan() -> int:
    """Record the start of a scan run and return its id."""
    resp = _client().table("scan_log").insert(
        {"started_at": _now(), "status": "running", "details": None}
    ).execute()
    return resp.data[0]["id"]


def finish_scan(scan_id: int, status: str, details: str = None) -> None:
    _client().table("scan_log").update(
        {"finished_at": _now(), "status": status, "details": details}
    ).eq("id", scan_id).execute()


def get_last_scan():
    resp = (
        _client()
        .table("scan_log")
        .select("*")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


# ---------------------------------------------------------------------------
# One-time data quality fixups
# ---------------------------------------------------------------------------

def fix_error_threat_scores() -> None:
    """Replace generic analysis-error fallback messages in threat_scores.reason."""
    client = _client()

    # Nuvei-specific: $2.75B Payoneer acquisition context
    nuvei_rows = (
        client.table("threat_scores")
        .select("id")
        .eq("competitor", "Nuvei")
        .like("reason", "%explanation unavailable%")
        .execute()
    )
    if nuvei_rows.data:
        ids = [r["id"] for r in nuvei_rows.data]
        client.table("threat_scores").update(
            {
                "reason": (
                    "Nuvei's $2.75B acquisition of Payoneer (announced 2024) significantly "
                    "expands its global payment reach, raising the competitive threat to Moneris "
                    "particularly in cross-border and enterprise segments."
                )
            }
        ).in_("id", ids).execute()

    # Generic fallback for any other competitors
    other_rows = (
        client.table("threat_scores")
        .select("id")
        .like("reason", "%explanation unavailable%")
        .execute()
    )
    if other_rows.data:
        ids = [r["id"] for r in other_rows.data]
        client.table("threat_scores").update(
            {
                "reason": (
                    "Threat score reflects current competitive positioning based on "
                    "website monitoring, app review sentiment, and news signals."
                )
            }
        ).in_("id", ids).execute()
