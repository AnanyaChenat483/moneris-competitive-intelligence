-- Moneris Competitive Intelligence Monitor — Supabase Schema
-- Run this entire script in the Supabase SQL Editor (https://app.supabase.com → SQL Editor)
-- before launching the app for the first time.

-- Snapshots: latest scraped content hash per competitor page (one row per competitor+page_type pair)
CREATE TABLE IF NOT EXISTS snapshots (
    competitor   TEXT NOT NULL,
    page_type    TEXT NOT NULL,
    url          TEXT NOT NULL,
    page_title   TEXT,
    content_hash TEXT NOT NULL,
    content_text TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (competitor, page_type)
);

-- Website changes: every detected content change that passed the impact threshold
CREATE TABLE IF NOT EXISTS website_changes (
    id                    BIGSERIAL PRIMARY KEY,
    detected_at           TEXT NOT NULL,
    competitor            TEXT NOT NULL,
    page_type             TEXT NOT NULL,
    url                   TEXT NOT NULL,
    change_type           TEXT NOT NULL,
    description           TEXT NOT NULL,
    customer_impact_score INTEGER NOT NULL,
    revenue_sensitivity   TEXT NOT NULL,
    segment_affected      TEXT NOT NULL,
    diff                  TEXT NOT NULL
);

-- Review sentiment: Google Play Store analysis result per competitor per scan
CREATE TABLE IF NOT EXISTS review_sentiment (
    id                   BIGSERIAL PRIMARY KEY,
    scanned_at           TEXT NOT NULL,
    competitor           TEXT NOT NULL,
    sentiment            TEXT NOT NULL,
    severity_score       REAL NOT NULL,
    themes               JSONB NOT NULL DEFAULT '[]',
    top_complaints       JSONB NOT NULL DEFAULT '[]',
    top_praise           JSONB NOT NULL DEFAULT '[]',
    moneris_opportunity  TEXT NOT NULL,
    source_breakdown     JSONB NOT NULL DEFAULT '{}',
    review_count         INTEGER NOT NULL
);

-- News articles: competitor news scored for Moneris relevance; unique per competitor+url
CREATE TABLE IF NOT EXISTS news_articles (
    id                    BIGSERIAL PRIMARY KEY,
    fetched_at            TEXT NOT NULL,
    competitor            TEXT NOT NULL,
    headline              TEXT NOT NULL,
    source                TEXT,
    url                   TEXT NOT NULL,
    published_at          TEXT,
    impact_type           TEXT NOT NULL,
    relevance_to_moneris  INTEGER NOT NULL,
    market_impact         TEXT NOT NULL,
    summary               TEXT NOT NULL,
    source_weight         TEXT NOT NULL,
    UNIQUE (competitor, url)
);

-- Threat scores: weighted composite score per competitor per scan run
-- Column is named reddit_component for historical reasons; it stores the app review sentiment component.
CREATE TABLE IF NOT EXISTS threat_scores (
    id                          BIGSERIAL PRIMARY KEY,
    scanned_at                  TEXT NOT NULL,
    competitor                  TEXT NOT NULL,
    threat_score                REAL NOT NULL,
    reddit_component            REAL NOT NULL,
    news_component              REAL NOT NULL,
    feature_velocity_component  REAL NOT NULL,
    smb_relevance_component     REAL NOT NULL,
    reason                      TEXT NOT NULL
);

-- Comparison cards: AI-generated Moneris vs all competitors card per scan
CREATE TABLE IF NOT EXISTS comparison_cards (
    id              BIGSERIAL PRIMARY KEY,
    generated_at    TEXT NOT NULL,
    comparison_json JSONB NOT NULL,
    top_threats     JSONB NOT NULL DEFAULT '[]',
    top_advantages  JSONB NOT NULL DEFAULT '[]'
);

-- Historical events: real competitive events 2022-2025 used to seed the Trends chart baseline
CREATE TABLE IF NOT EXISTS historical_events (
    id           BIGSERIAL PRIMARY KEY,
    competitor   TEXT NOT NULL,
    date         TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    description  TEXT NOT NULL,
    source       TEXT NOT NULL,
    impact_score INTEGER NOT NULL
);

-- Scan log: audit trail of every scan run
CREATE TABLE IF NOT EXISTS scan_log (
    id           BIGSERIAL PRIMARY KEY,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    status       TEXT NOT NULL,
    details      TEXT
);
