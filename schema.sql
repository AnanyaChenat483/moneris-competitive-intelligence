-- Moneris Competitive Intelligence Monitor — Supabase Schema
-- Run this entire script in the Supabase SQL Editor (https://app.supabase.com → SQL Editor)
-- before launching the app for the first time.
--
-- IMPORTANT: Row Level Security (RLS) is explicitly DISABLED on every table below.
-- Without this, Supabase silently blocks all reads/writes when using the anon key,
-- causing snapshots to never be found and changes to never be saved.
-- If you later add authentication, re-enable RLS and add appropriate policies.

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
ALTER TABLE snapshots DISABLE ROW LEVEL SECURITY;

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
ALTER TABLE website_changes DISABLE ROW LEVEL SECURITY;

-- Product intelligence: Claude's mapping of each detected product_updates change to
-- the Moneris product area it threatens, or the gap it reveals (moneris_product =
-- 'No Moneris equivalent (gap)' — there is no separate boolean gap flag; that value
-- is the single source of truth for gap status). One row per detected product-update
-- change; powers the Product Intelligence tab. page_type holds the specific source
-- page label (e.g. "Changelog", "Newsroom"); raw_change holds the underlying
-- website-change description this mapping was derived from.
CREATE TABLE IF NOT EXISTS product_intelligence (
    id                  BIGSERIAL PRIMARY KEY,
    detected_at         TEXT NOT NULL,
    analyzed_at         TEXT NOT NULL,
    competitor          TEXT NOT NULL,
    page_type           TEXT NOT NULL,
    url                 TEXT NOT NULL,
    raw_change          TEXT NOT NULL,
    competitor_move     TEXT NOT NULL,
    moneris_product     TEXT NOT NULL,
    threat_level        TEXT NOT NULL,
    recommended_action  TEXT NOT NULL
);
ALTER TABLE product_intelligence DISABLE ROW LEVEL SECURITY;

-- Social intelligence: Claude's synthesis of each competitor's LinkedIn (via Google
-- News proxy — LinkedIn has no public post feed for unauthenticated requests) and
-- YouTube signal into 5 fields. One row per scan per competitor; powers the Social
-- Channels tab. target_segment_signals is a JSON array since a competitor's social
-- activity can target more than one Moneris segment at once.
CREATE TABLE IF NOT EXISTS social_intelligence (
    id                     BIGSERIAL PRIMARY KEY,
    analyzed_at            TEXT NOT NULL,
    competitor             TEXT NOT NULL,
    messaging_theme        TEXT NOT NULL,
    campaign_focus         TEXT NOT NULL,
    target_segment_signals JSONB NOT NULL DEFAULT '[]',
    tone_shift             TEXT NOT NULL,
    moneris_opportunity    TEXT NOT NULL,
    linkedin_signal_count  INTEGER NOT NULL DEFAULT 0,
    youtube_signal_count   INTEGER NOT NULL DEFAULT 0
);
ALTER TABLE social_intelligence DISABLE ROW LEVEL SECURITY;

-- Offers & promotions intelligence: Claude's classification of each detected change
-- on a competitor's pricing/promo page. One row per detected offer-page change;
-- powers the Offers & Promotions tab and its Moneris Gap Summary.
CREATE TABLE IF NOT EXISTS offers_intelligence (
    id             BIGSERIAL PRIMARY KEY,
    detected_at    TEXT NOT NULL,
    analyzed_at    TEXT NOT NULL,
    competitor     TEXT NOT NULL,
    page_type      TEXT NOT NULL,
    url            TEXT NOT NULL,
    description    TEXT NOT NULL,
    offer_type     TEXT NOT NULL,
    target_segment TEXT NOT NULL,
    aggressiveness TEXT NOT NULL,
    duration       TEXT NOT NULL,
    moneris_gap    TEXT NOT NULL
);
ALTER TABLE offers_intelligence DISABLE ROW LEVEL SECURITY;

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
ALTER TABLE review_sentiment DISABLE ROW LEVEL SECURITY;

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
ALTER TABLE news_articles DISABLE ROW LEVEL SECURITY;

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
ALTER TABLE threat_scores DISABLE ROW LEVEL SECURITY;

-- Comparison cards: AI-generated Moneris vs all competitors card per scan
CREATE TABLE IF NOT EXISTS comparison_cards (
    id              BIGSERIAL PRIMARY KEY,
    generated_at    TEXT NOT NULL,
    comparison_json JSONB NOT NULL,
    top_threats     JSONB NOT NULL DEFAULT '[]',
    top_advantages  JSONB NOT NULL DEFAULT '[]'
);
ALTER TABLE comparison_cards DISABLE ROW LEVEL SECURITY;

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
ALTER TABLE historical_events DISABLE ROW LEVEL SECURITY;

-- Scan log: audit trail of every scan run
CREATE TABLE IF NOT EXISTS scan_log (
    id           BIGSERIAL PRIMARY KEY,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    status       TEXT NOT NULL,
    details      TEXT
);
ALTER TABLE scan_log DISABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- OPTIONAL: keep RLS enabled instead of disabled
-- ---------------------------------------------------------------------------
-- This app is a single-tenant internal dashboard with no per-user data
-- isolation — the anon key IS the app's only credential, so disabling RLS
-- (above) is the simplest correct setup and is what this schema uses by
-- default. If you'd rather leave RLS ON (e.g. for a stricter security
-- posture or an org policy that requires it), run the block below INSTEAD
-- of the DISABLE statements above: it re-enables RLS and adds an explicit
-- policy granting the anon role full access on every table, which is
-- functionally equivalent to disabling RLS but auditable as an explicit
-- policy. Do not run both blocks against the same table — whichever runs
-- last wins, and a stray "ENABLE ROW LEVEL SECURITY" with no matching
-- policy silently blocks every read/write for the anon key (this is the
-- most common cause of a Supabase-backed Streamlit app crashing right
-- after RLS is toggled on in the Supabase dashboard).
--
-- DO $$
-- DECLARE
--     t TEXT;
-- BEGIN
--     FOR t IN SELECT unnest(ARRAY['snapshots', 'website_changes', 'product_intelligence',
--                                   'social_intelligence', 'offers_intelligence',
--                                   'review_sentiment', 'news_articles', 'threat_scores',
--                                   'comparison_cards', 'historical_events', 'scan_log'])
--     LOOP
--         EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
--         EXECUTE format('DROP POLICY IF EXISTS anon_full_access ON %I', t);
--         EXECUTE format(
--             'CREATE POLICY anon_full_access ON %I FOR ALL TO anon USING (true) WITH CHECK (true)', t
--         );
--     END LOOP;
-- END $$;
