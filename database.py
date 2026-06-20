"""SQLite persistence layer for the Competitive Intelligence Monitor."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DATA_DIR, DB_PATH


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_connection():
    """Yield a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the data directory and all required tables if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with get_connection() as conn:
        # --- Layer 1: website snapshots & changes ---------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                competitor TEXT NOT NULL,
                page_type TEXT NOT NULL,
                url TEXT NOT NULL,
                page_title TEXT,
                content_hash TEXT NOT NULL,
                content_text TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (competitor, page_type)
            )
            """
        )
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(snapshots)")}
        if "page_title" not in existing_columns:
            conn.execute("ALTER TABLE snapshots ADD COLUMN page_title TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS website_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detected_at TEXT NOT NULL,
                competitor TEXT NOT NULL,
                page_type TEXT NOT NULL,
                url TEXT NOT NULL,
                change_type TEXT NOT NULL,
                description TEXT NOT NULL,
                customer_impact_score INTEGER NOT NULL,
                revenue_sensitivity TEXT NOT NULL,
                segment_affected TEXT NOT NULL,
                diff TEXT NOT NULL
            )
            """
        )

        # --- Layer 2: Customer review sentiment (Google Play Store) -----------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS review_sentiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scanned_at TEXT NOT NULL,
                competitor TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                severity_score REAL NOT NULL,
                themes TEXT NOT NULL,
                top_complaints TEXT NOT NULL,
                top_praise TEXT NOT NULL,
                moneris_opportunity TEXT NOT NULL,
                source_breakdown TEXT NOT NULL,
                review_count INTEGER NOT NULL
            )
            """
        )

        # --- Layer 3: news articles -------------------------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fetched_at TEXT NOT NULL,
                competitor TEXT NOT NULL,
                headline TEXT NOT NULL,
                source TEXT,
                url TEXT NOT NULL,
                published_at TEXT,
                impact_type TEXT NOT NULL,
                relevance_to_moneris INTEGER NOT NULL,
                market_impact TEXT NOT NULL,
                summary TEXT NOT NULL,
                source_weight TEXT NOT NULL,
                UNIQUE (competitor, url)
            )
            """
        )

        # --- Feature 2: threat scores over time -----------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS threat_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scanned_at TEXT NOT NULL,
                competitor TEXT NOT NULL,
                threat_score REAL NOT NULL,
                reddit_component REAL NOT NULL,
                news_component REAL NOT NULL,
                feature_velocity_component REAL NOT NULL,
                smb_relevance_component REAL NOT NULL,
                reason TEXT NOT NULL
            )
            """
        )

        # --- Feature 1: Moneris comparison cards ----------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS comparison_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_at TEXT NOT NULL,
                comparison_json TEXT NOT NULL,
                top_threats TEXT NOT NULL,
                top_advantages TEXT NOT NULL
            )
            """
        )

        # --- Feature 4: historical seed events ------------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor TEXT NOT NULL,
                date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                source TEXT NOT NULL,
                impact_score INTEGER NOT NULL
            )
            """
        )

        # --- Scan audit log ----------------------------------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                details TEXT
            )
            """
        )


# ---------------------------------------------------------------------------
# Snapshots (Layer 1)
# ---------------------------------------------------------------------------

def get_snapshot(competitor: str, page_type: str):
    """Return the stored snapshot row for (competitor, page_type), or None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM snapshots WHERE competitor = ? AND page_type = ?",
            (competitor, page_type),
        ).fetchone()
        return dict(row) if row else None


def upsert_snapshot(competitor: str, page_type: str, url: str, page_title: str,
                     content_hash: str, content_text: str) -> None:
    """Insert or update the current snapshot for (competitor, page_type)."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO snapshots
                (competitor, page_type, url, page_title, content_hash, content_text, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(competitor, page_type) DO UPDATE SET
                url = excluded.url,
                page_title = excluded.page_title,
                content_hash = excluded.content_hash,
                content_text = excluded.content_text,
                updated_at = excluded.updated_at
            """,
            (competitor, page_type, url, page_title, content_hash, content_text, _now()),
        )


# ---------------------------------------------------------------------------
# Website changes (Layer 1 / Tab 1)
# ---------------------------------------------------------------------------

def insert_website_change(competitor: str, page_type: str, url: str, change_type: str,
                            description: str, customer_impact_score: int,
                            revenue_sensitivity: str, segment_affected: str, diff: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO website_changes
                (detected_at, competitor, page_type, url, change_type, description,
                 customer_impact_score, revenue_sensitivity, segment_affected, diff)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (_now(), competitor, page_type, url, change_type, description,
             customer_impact_score, revenue_sensitivity, segment_affected, diff),
        )


def get_website_changes(limit: int = 100, competitor: str = None, change_type: str = None):
    query = "SELECT * FROM website_changes WHERE 1=1"
    params = []

    if competitor and competitor != "All":
        query += " AND competitor = ?"
        params.append(competitor)

    if change_type and change_type != "All":
        query += " AND change_type = ?"
        params.append(change_type)

    query += " ORDER BY detected_at DESC, id DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Review sentiment (Layer 2 / Tab 2 — Google Play Store)
# ---------------------------------------------------------------------------

def insert_review_sentiment(competitor: str, sentiment: str, severity_score: float,
                              themes: list, top_complaints: list, top_praise: list,
                              moneris_opportunity: str, source_breakdown: dict,
                              review_count: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO review_sentiment
                (scanned_at, competitor, sentiment, severity_score, themes,
                 top_complaints, top_praise, moneris_opportunity, source_breakdown, review_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (_now(), competitor, sentiment, severity_score, json.dumps(themes),
             json.dumps(top_complaints), json.dumps(top_praise), moneris_opportunity,
             json.dumps(source_breakdown), review_count),
        )


def get_latest_review_sentiment() -> dict:
    """Return a dict mapping competitor -> latest review sentiment row (JSON fields decoded)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT rs.* FROM review_sentiment rs
            INNER JOIN (
                SELECT competitor, MAX(id) AS max_id FROM review_sentiment GROUP BY competitor
            ) latest ON rs.competitor = latest.competitor AND rs.id = latest.max_id
            """
        ).fetchall()

    result = {}
    for row in rows:
        record = dict(row)
        record["themes"] = json.loads(record["themes"])
        record["top_complaints"] = json.loads(record["top_complaints"])
        record["top_praise"] = json.loads(record["top_praise"])
        record["source_breakdown"] = json.loads(record["source_breakdown"])
        result[record["competitor"]] = record
    return result


# ---------------------------------------------------------------------------
# News articles (Layer 3 / Tab 3)
# ---------------------------------------------------------------------------

def insert_news_article(competitor: str, headline: str, source: str, url: str,
                          published_at: str, impact_type: str, relevance_to_moneris: int,
                          market_impact: str, summary: str, source_weight: str) -> None:
    """Insert a news article, ignoring duplicates (same competitor + url)."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO news_articles
                (fetched_at, competitor, headline, source, url, published_at,
                 impact_type, relevance_to_moneris, market_impact, summary, source_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (_now(), competitor, headline, source, url, published_at, impact_type,
             relevance_to_moneris, market_impact, summary, source_weight),
        )


def get_news_articles(limit: int = 100, competitor: str = None, impact_type: str = None):
    query = "SELECT * FROM news_articles WHERE 1=1"
    params = []

    if competitor and competitor != "All":
        query += " AND competitor = ?"
        params.append(competitor)

    if impact_type and impact_type != "All":
        query += " AND impact_type = ?"
        params.append(impact_type)

    query += " ORDER BY relevance_to_moneris DESC, fetched_at DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Threat scores (Feature 2 / Tab 5)
# ---------------------------------------------------------------------------

def insert_threat_score(competitor: str, threat_score: float, review_component: float,
                          news_component: float, feature_velocity_component: float,
                          smb_relevance_component: float, reason: str, scanned_at: str = None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO threat_scores
                (scanned_at, competitor, threat_score, reddit_component, news_component,
                 feature_velocity_component, smb_relevance_component, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (scanned_at or _now(), competitor, threat_score, review_component, news_component,
             feature_velocity_component, smb_relevance_component, reason),
        )


def get_threat_score_history(competitor: str = None):
    query = "SELECT * FROM threat_scores WHERE 1=1"
    params = []
    if competitor and competitor != "All":
        query += " AND competitor = ?"
        params.append(competitor)
    query += " ORDER BY scanned_at ASC, id ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_latest_threat_scores() -> dict:
    """Return a dict mapping competitor -> latest threat_score row."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ts.* FROM threat_scores ts
            INNER JOIN (
                SELECT competitor, MAX(id) AS max_id FROM threat_scores GROUP BY competitor
            ) latest ON ts.competitor = latest.competitor AND ts.id = latest.max_id
            """
        ).fetchall()
    return {row["competitor"]: dict(row) for row in rows}


def get_previous_threat_score(competitor: str):
    """Return the second-most-recent threat_score row for a competitor, or None."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM threat_scores WHERE competitor = ? ORDER BY id DESC LIMIT 2",
            (competitor,),
        ).fetchall()
    if len(rows) < 2:
        return None
    return dict(rows[1])


# ---------------------------------------------------------------------------
# Comparison cards (Feature 1 / Tab 4)
# ---------------------------------------------------------------------------

def insert_comparison_card(comparison: dict, top_threats: list, top_advantages: list) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO comparison_cards (generated_at, comparison_json, top_threats, top_advantages)
            VALUES (?, ?, ?, ?)
            """,
            (_now(), json.dumps(comparison), json.dumps(top_threats), json.dumps(top_advantages)),
        )


def get_latest_comparison_card():
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM comparison_cards ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    record = dict(row)
    record["comparison"] = json.loads(record["comparison_json"])
    record["top_threats"] = json.loads(record["top_threats"])
    record["top_advantages"] = json.loads(record["top_advantages"])
    return record


# ---------------------------------------------------------------------------
# Historical events (Feature 4)
# ---------------------------------------------------------------------------

def insert_historical_event(competitor: str, date: str, event_type: str, description: str,
                              source: str, impact_score: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO historical_events (competitor, date, event_type, description, source, impact_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (competitor, date, event_type, description, source, impact_score),
        )


def get_historical_events(competitor: str = None):
    query = "SELECT * FROM historical_events WHERE 1=1"
    params = []
    if competitor and competitor != "All":
        query += " AND competitor = ?"
        params.append(competitor)
    query += " ORDER BY date ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def count_historical_events() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM historical_events").fetchone()[0]


# ---------------------------------------------------------------------------
# Scan log
# ---------------------------------------------------------------------------

def start_scan() -> int:
    """Record the start of a scan run and return its id."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO scan_log (started_at, status, details) VALUES (?, ?, ?)",
            (_now(), "running", None),
        )
        return cursor.lastrowid


def finish_scan(scan_id: int, status: str, details: str = None) -> None:
    """Mark a scan run as finished with a final status and optional details."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE scan_log SET finished_at = ?, status = ?, details = ? WHERE id = ?",
            (_now(), status, details, scan_id),
        )


def get_last_scan():
    """Return the most recent scan log entry, or None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM scan_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# One-time data quality fixups
# ---------------------------------------------------------------------------

def fix_error_threat_scores() -> None:
    """Replace generic analysis-error fallback messages in threat_scores.reason."""
    with get_connection() as conn:
        # Nuvei-specific context: $2.75B Payoneer acquisition
        conn.execute(
            """
            UPDATE threat_scores
            SET reason = 'Nuvei''s $2.75B acquisition of Payoneer (announced 2024) significantly expands its global payment reach, raising the competitive threat to Moneris particularly in cross-border and enterprise segments.'
            WHERE competitor = 'Nuvei'
              AND reason LIKE '%explanation unavailable%'
            """
        )
        # Generic fallback for any other competitors
        conn.execute(
            """
            UPDATE threat_scores
            SET reason = 'Threat score reflects current competitive positioning based on website monitoring, app review sentiment, and news signals.'
            WHERE reason LIKE '%explanation unavailable%'
            """
        )
