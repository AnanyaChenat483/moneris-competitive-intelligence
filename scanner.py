"""Orchestrates all three data layers, AI analysis, threat scoring, and storage."""

import difflib
import hashlib

import database
from analyzer import (
    analyze_news_batch,
    analyze_offer_change,
    analyze_product_intelligence,
    analyze_review_sentiment,
    analyze_social_intelligence,
    analyze_website_change,
    explain_threat_score_change,
    generate_comparison_card,
)
from config import (
    COMPETITORS,
    OFFERS_PAGES,
    PRODUCT_UPDATE_PAGE_TYPE,
    PRODUCT_UPDATE_PAGES,
    SMB_RELEVANCE,
    SOCIAL_PAGES,
    THREAT_WEIGHTS,
)
from news_client import NewsError, fetch_news_for_competitor
from play_reviews import get_reviews_for_competitor
from scraper import (
    ScrapeError,
    content_to_text,
    product_update_content_to_text,
    scrape_page,
    scrape_product_update_page,
)
from social_client import SocialFetchError, fetch_linkedin_signal, fetch_youtube_uploads

FEATURE_VELOCITY_BASELINE = 2.0  # used when no website changes detected this scan
NEWS_MOMENTUM_BASELINE = 3.0  # used when no news articles are available this scan


# Streamlit Cloud captures stdout — use print(flush=True) so these show up in
# server logs even though the sidebar's live log only keeps the last 25 lines.
def _log(msg: str) -> None:
    print(f"[SCAN] {msg}", flush=True)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_diff(old_text: str, new_text: str) -> str:
    diff_lines = difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        lineterm="",
        fromfile="previous",
        tofile="current",
    )
    return "\n".join(diff_lines)


def _scan_website(competitor: str, report) -> list[dict]:
    """Scrape all configured pages for a competitor and return detected changes."""
    detected_changes = []

    for page_type, url in COMPETITORS[competitor].items():
        report(f"  [Website] {page_type}: {url}")

        try:
            content = scrape_page(url)
        except ScrapeError as exc:
            report(f"    Error: {exc}")
            continue

        new_text = content_to_text(content)
        new_hash = _hash_text(new_text)
        snapshot = database.get_snapshot(competitor, page_type)

        if snapshot is None:
            database.upsert_snapshot(competitor, page_type, url, content.get("title", ""), new_hash, new_text)
            report("    No previous snapshot - baseline stored.")
            continue

        if snapshot["content_hash"] == new_hash:
            report("    No changes detected.")
            continue

        old_text = snapshot["content_text"]
        diff_text = _build_diff(old_text, new_text)

        try:
            analysis = analyze_website_change(
                competitor=competitor,
                page_type=page_type,
                url=url,
                old_text=old_text,
                new_text=new_text,
                diff_text=diff_text,
            )
        except Exception as exc:
            report(f"    Change detected, but analysis failed: {exc}")
            database.upsert_snapshot(competitor, page_type, url, content.get("title", ""), new_hash, new_text)
            continue

        if analysis["customer_impact_score"] < 2:
            report(f"    Low-impact change ({analysis['customer_impact_score']}/10) skipped — below minimum threshold.")
            database.upsert_snapshot(competitor, page_type, url, content.get("title", ""), new_hash, new_text)
            continue

        database.insert_website_change(
            competitor=competitor,
            page_type=page_type,
            url=url,
            change_type=analysis["change_type"],
            description=analysis["description"],
            customer_impact_score=analysis["customer_impact_score"],
            revenue_sensitivity=analysis["revenue_sensitivity"],
            segment_affected=analysis["segment_affected"],
            diff=diff_text,
        )
        database.upsert_snapshot(competitor, page_type, url, content.get("title", ""), new_hash, new_text)

        detected_changes.append(analysis)
        report(
            f"    Change detected ({analysis['change_type']}, impact "
            f"{analysis['customer_impact_score']}/10): {analysis['description']}"
        )

    return detected_changes


def _scan_product_updates(competitor: str, report) -> list[dict]:
    """Scrape changelog/newsroom/roadmap pages for a competitor and return detected changes.

    Mirrors _scan_website, but targets richer product-signal pages (Layer 1b)
    and stores every change under page_type=PRODUCT_UPDATE_PAGE_TYPE so the
    Product Intelligence tab can query them independently. Snapshot keys are
    prefixed to avoid colliding with the main COMPETITORS page labels.
    """
    detected_changes = []
    pages = PRODUCT_UPDATE_PAGES.get(competitor, {})
    _log(f"{competitor}: {len(pages)} product-update page(s) configured: {list(pages.keys())}")

    for label, url in pages.items():
        snapshot_key = f"product_updates::{label}"
        report(f"  [Product Updates] {label}: {url}")
        _log(f"{competitor} / {label}: fetching {url}")

        try:
            content = scrape_product_update_page(url)
        except ScrapeError as exc:
            report(f"    Error: {exc}")
            _log(f"{competitor} / {label}: SCRAPE FAILED — {exc}")
            continue

        new_text = product_update_content_to_text(content)
        new_hash = _hash_text(new_text)
        _log(
            f"{competitor} / {label}: fetched OK — title={content.get('title', '')!r} "
            f"headings={len(content.get('headings', []))} "
            f"article_titles={len(content.get('article_titles', []))} "
            f"body_paragraphs={len(content.get('body_paragraphs', []))} "
            f"text_len={len(new_text)} hash={new_hash[:12]}"
        )

        snapshot = database.get_snapshot(competitor, snapshot_key)

        if snapshot is None:
            database.upsert_snapshot(competitor, snapshot_key, url, content.get("title", ""), new_hash, new_text)
            report("    No previous snapshot - baseline stored.")
            _log(f"{competitor} / {label}: no previous snapshot — baseline stored, nothing to diff yet.")
            continue

        if snapshot["content_hash"] == new_hash:
            report("    No changes detected.")
            _log(f"{competitor} / {label}: hash unchanged since last scan — no diff.")
            continue

        old_text = snapshot["content_text"]
        diff_text = _build_diff(old_text, new_text)
        _log(f"{competitor} / {label}: content changed — calling analyze_website_change()")

        try:
            analysis = analyze_website_change(
                competitor=competitor,
                page_type=label,
                url=url,
                old_text=old_text,
                new_text=new_text,
                diff_text=diff_text,
            )
        except Exception as exc:
            report(f"    Change detected, but analysis failed: {exc}")
            _log(f"{competitor} / {label}: analyze_website_change FAILED — {exc}")
            database.upsert_snapshot(competitor, snapshot_key, url, content.get("title", ""), new_hash, new_text)
            continue

        _log(
            f"{competitor} / {label}: analyze_website_change OK — "
            f"impact={analysis['customer_impact_score']} type={analysis['change_type']}"
        )

        if analysis["customer_impact_score"] < 2:
            report(f"    Low-impact change ({analysis['customer_impact_score']}/10) skipped — below minimum threshold.")
            _log(f"{competitor} / {label}: impact {analysis['customer_impact_score']} < 2 — skipped, no rows inserted.")
            database.upsert_snapshot(competitor, snapshot_key, url, content.get("title", ""), new_hash, new_text)
            continue

        change_id = database.insert_website_change(
            competitor=competitor,
            page_type=PRODUCT_UPDATE_PAGE_TYPE,
            url=url,
            change_type=analysis["change_type"],
            description=analysis["description"],
            customer_impact_score=analysis["customer_impact_score"],
            revenue_sensitivity=analysis["revenue_sensitivity"],
            segment_affected=analysis["segment_affected"],
            diff=diff_text,
        )
        database.upsert_snapshot(competitor, snapshot_key, url, content.get("title", ""), new_hash, new_text)
        _log(f"{competitor} / {label}: inserted website_changes row id={change_id} (page_type={PRODUCT_UPDATE_PAGE_TYPE})")

        try:
            _log(f"{competitor} / {label}: calling analyze_product_intelligence()")
            mapping = analyze_product_intelligence(
                competitor=competitor,
                page_label=label,
                url=url,
                change_type=analysis["change_type"],
                description=analysis["description"],
            )
            _log(
                f"{competitor} / {label}: analyze_product_intelligence OK — "
                f"product={mapping['moneris_product']!r} threat={mapping['threat_level']}"
            )
            database.insert_product_intelligence(
                competitor=competitor,
                page_type=label,
                url=url,
                raw_change=analysis["description"],
                competitor_move=mapping["competitor_move"],
                moneris_product=mapping["moneris_product"],
                threat_level=mapping["threat_level"],
                recommended_action=mapping["recommended_action"],
            )
            _log(f"{competitor} / {label}: inserted product_intelligence row (linked to website_changes id={change_id})")
        except Exception as exc:
            report(f"    Product intelligence mapping failed: {exc}")
            _log(f"{competitor} / {label}: PRODUCT INTELLIGENCE FAILED — {type(exc).__name__}: {exc}")

        detected_changes.append(analysis)
        report(
            f"    Change detected ({analysis['change_type']}, impact "
            f"{analysis['customer_impact_score']}/10): {analysis['description']}"
        )

    return detected_changes


def _scan_social(competitor: str, report) -> dict | None:
    """Fetch LinkedIn (Google News proxy) + YouTube signal for a competitor and synthesize it.

    Runs once per competitor per scan (no diffing — social signal is
    resynthesized fresh each time, unlike the change-detection layers).
    Returns the synthesized dict, or None if no social pages are configured
    or both signal sources came back empty/failed.
    """
    pages = SOCIAL_PAGES.get(competitor)
    if not pages:
        return None

    linkedin_query = pages.get("linkedin_query")
    youtube_channel_id = pages.get("youtube_channel_id")

    linkedin_items = []
    if linkedin_query:
        report(f"  [Social] LinkedIn (via Google News): {linkedin_query!r}")
        try:
            linkedin_items = fetch_linkedin_signal(competitor, linkedin_query)
            _log(f"{competitor} / LinkedIn: fetched {len(linkedin_items)} result(s)")
        except SocialFetchError as exc:
            report(f"    Error: {exc}")
            _log(f"{competitor} / LinkedIn: FETCH FAILED — {exc}")

    youtube_items = []
    if youtube_channel_id:
        report(f"  [Social] YouTube: channel_id={youtube_channel_id}")
        try:
            youtube_items = fetch_youtube_uploads(competitor, youtube_channel_id)
            _log(f"{competitor} / YouTube: fetched {len(youtube_items)} upload(s)")
        except SocialFetchError as exc:
            report(f"    Error: {exc}")
            _log(f"{competitor} / YouTube: FETCH FAILED — {exc}")

    if not linkedin_items and not youtube_items:
        report("    No social signal available this scan.")
        return None

    try:
        _log(f"{competitor} / Social: calling analyze_social_intelligence()")
        result = analyze_social_intelligence(competitor, linkedin_items, youtube_items)
    except Exception as exc:
        report(f"    Social intelligence analysis failed: {exc}")
        _log(f"{competitor} / Social: ANALYSIS FAILED — {type(exc).__name__}: {exc}")
        return None

    database.insert_social_intelligence(
        competitor=competitor,
        messaging_theme=result["messaging_theme"],
        campaign_focus=result["campaign_focus"],
        target_segment_signals=result["target_segment_signals"],
        tone_shift=result["tone_shift"],
        moneris_opportunity=result["moneris_opportunity"],
        linkedin_signal_count=len(linkedin_items),
        youtube_signal_count=len(youtube_items),
    )
    _log(f"{competitor} / Social: inserted social_intelligence row")
    report(f"    Social signal synthesized: {result['campaign_focus']} / {result['tone_shift']}")

    return result


def _scan_offers(competitor: str, report) -> list[dict]:
    """Scrape pricing/promo pages for a competitor and classify detected changes as offers.

    Mirrors _scan_website / _scan_product_updates: snapshot-diff each
    configured offers page, and only classify+store when real content
    changed. Snapshot keys are prefixed to avoid colliding with the other
    two page-tracking layers that may share the same URL.
    """
    detected = []
    pages = OFFERS_PAGES.get(competitor, {})

    for label, url in pages.items():
        snapshot_key = f"offers::{label}"
        report(f"  [Offers] {label}: {url}")
        _log(f"{competitor} / {label}: fetching {url}")

        try:
            content = scrape_page(url)
        except ScrapeError as exc:
            report(f"    Error: {exc}")
            _log(f"{competitor} / {label}: SCRAPE FAILED — {exc}")
            continue

        new_text = content_to_text(content)
        new_hash = _hash_text(new_text)
        snapshot = database.get_snapshot(competitor, snapshot_key)

        if snapshot is None:
            database.upsert_snapshot(competitor, snapshot_key, url, content.get("title", ""), new_hash, new_text)
            report("    No previous snapshot - baseline stored.")
            _log(f"{competitor} / {label}: no previous snapshot — baseline stored.")
            continue

        if snapshot["content_hash"] == new_hash:
            report("    No changes detected.")
            continue

        old_text = snapshot["content_text"]
        diff_text = _build_diff(old_text, new_text)

        try:
            offer = analyze_offer_change(competitor, label, url, diff_text)
        except Exception as exc:
            report(f"    Change detected, but offer classification failed: {exc}")
            _log(f"{competitor} / {label}: OFFER ANALYSIS FAILED — {exc}")
            database.upsert_snapshot(competitor, snapshot_key, url, content.get("title", ""), new_hash, new_text)
            continue

        database.insert_offers_intelligence(
            competitor=competitor,
            page_type=label,
            url=url,
            description=offer["description"],
            offer_type=offer["offer_type"],
            target_segment=offer["target_segment"],
            aggressiveness=offer["aggressiveness"],
            duration=offer["duration"],
            moneris_gap=offer["moneris_gap"],
        )
        database.upsert_snapshot(competitor, snapshot_key, url, content.get("title", ""), new_hash, new_text)
        _log(f"{competitor} / {label}: inserted offers_intelligence row (offer_type={offer['offer_type']})")

        detected.append(offer)
        report(f"    Offer detected ({offer['offer_type']}, {offer['aggressiveness']} aggressiveness): {offer['description']}")

    return detected


def _scan_reviews(competitor: str, report) -> dict:
    """Fetch Google Play Store reviews and analyze sentiment for a competitor."""
    reviews = get_reviews_for_competitor(competitor, progress_callback=report)

    # Analyze with Claude; if Claude fails, still store the review count
    try:
        sentiment = analyze_review_sentiment(competitor, reviews)
    except Exception as exc:
        report(f"    Claude analysis failed: {exc} — storing count without AI analysis")
        sentiment = {
            "sentiment": "neutral", "severity_score": 5.0, "themes": [],
            "top_complaints": [], "top_praise": [],
            "moneris_opportunity": (
                f"Found {len(reviews)} Play Store review(s) but Claude analysis failed this scan."
                if reviews else "No Play Store reviews found for this competitor in this scan."
            ),
        }

    source_breakdown = {"Google Play": len(reviews)} if reviews else {}

    database.insert_review_sentiment(
        competitor=competitor,
        sentiment=sentiment["sentiment"],
        severity_score=sentiment["severity_score"],
        themes=sentiment["themes"],
        top_complaints=sentiment["top_complaints"],
        top_praise=sentiment["top_praise"],
        moneris_opportunity=sentiment["moneris_opportunity"],
        source_breakdown=source_breakdown,
        review_count=len(reviews),
    )

    report(f"    Sentiment: {sentiment['sentiment']} (severity {sentiment['severity_score']}/10)")
    return sentiment


def _scan_news(competitor: str, report) -> list[dict]:
    """Fetch and classify news articles for a competitor."""
    report(f"  [News] Fetching Google News for {competitor}...")

    try:
        articles = fetch_news_for_competitor(competitor)
    except NewsError as exc:
        report(f"    Error: {exc}")
        return []

    report(f"    Found {len(articles)} article(s).")
    if not articles:
        return []

    classifications = analyze_news_batch(competitor, articles)

    enriched = []
    for article, classification in zip(articles, classifications):
        enriched.append({**article, **classification})
        database.insert_news_article(
            competitor=competitor,
            headline=article["headline"],
            source=article["source"],
            url=article["url"],
            published_at=article["published_at"],
            impact_type=classification["impact_type"],
            relevance_to_moneris=classification["relevance_to_moneris"],
            market_impact=classification["market_impact"],
            summary=classification["summary"],
            source_weight=article["source_weight"],
        )

    return enriched


def _compute_threat_score(competitor: str, website_changes: list[dict],
                            sentiment: dict, news: list[dict]) -> tuple[float, dict]:
    """Compute the weighted threat score and its components for a competitor."""
    review_component = sentiment["severity_score"]

    if news:
        news_component = sum(a["relevance_to_moneris"] for a in news) / len(news)
    else:
        news_component = NEWS_MOMENTUM_BASELINE

    if website_changes:
        feature_velocity_component = sum(c["customer_impact_score"] for c in website_changes) / len(website_changes)
    else:
        feature_velocity_component = FEATURE_VELOCITY_BASELINE

    smb_relevance_component = SMB_RELEVANCE.get(competitor, 5)

    weights = THREAT_WEIGHTS
    threat_score = (
        weights["review_sentiment"] * review_component
        + weights["news_momentum"] * news_component
        + weights["feature_velocity"] * feature_velocity_component
        + weights["smb_relevance"] * smb_relevance_component
    )
    threat_score = round(max(1.0, min(10.0, threat_score)), 1)

    components = {
        "review_component": round(review_component, 1),
        "news_component": round(news_component, 1),
        "feature_velocity_component": round(feature_velocity_component, 1),
        "smb_relevance_component": float(smb_relevance_component),
    }
    return threat_score, components


def _build_signals_summary(competitor: str, website_changes: list[dict],
                             sentiment: dict, news: list[dict]) -> str:
    lines = []

    if website_changes:
        lines.append("Website changes detected this scan:")
        for c in website_changes:
            lines.append(f"  - ({c['change_type']}, impact {c['customer_impact_score']}/10) {c['description']}")
    else:
        lines.append("No website changes detected this scan.")

    lines.append(
        f"App review sentiment: {sentiment['sentiment']} (severity {sentiment['severity_score']}/10). "
        f"Themes: {', '.join(sentiment['themes']) if sentiment['themes'] else 'none'}."
    )

    if news:
        top_news = sorted(news, key=lambda a: a["relevance_to_moneris"], reverse=True)[:3]
        lines.append("Top news this scan:")
        for a in top_news:
            lines.append(f"  - (relevance {a['relevance_to_moneris']}/10) {a['headline']} - {a['summary']}")
    else:
        lines.append("No news articles found this scan.")

    return "\n".join(lines)


def _build_comparison_context(all_results: dict) -> str:
    """Build a text summary of this scan's findings across all competitors for the comparison card."""
    sections = []
    for competitor, result in all_results.items():
        lines = [f"## {competitor}"]
        if result["website_changes"]:
            for c in result["website_changes"]:
                lines.append(f"- Website ({c['change_type']}): {c['description']}")
        sentiment = result["sentiment"]
        lines.append(
            f"- App review sentiment: {sentiment['sentiment']} (severity {sentiment['severity_score']}/10), "
            f"themes: {', '.join(sentiment['themes']) if sentiment['themes'] else 'none'}"
        )
        if sentiment.get("moneris_opportunity"):
            lines.append(f"  Opportunity: {sentiment['moneris_opportunity']}")
        if result["news"]:
            for a in sorted(result["news"], key=lambda a: a["relevance_to_moneris"], reverse=True)[:2]:
                lines.append(f"- News: {a['headline']} ({a['impact_type']}, relevance {a['relevance_to_moneris']}/10)")
        lines.append(f"- Current threat score: {result['threat_score']}/10")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def run_scan(progress_callback=None) -> dict:
    """Run the full scan pipeline: website → play reviews → news → AI analysis → storage.

    progress_callback, if provided, is called with a string message after each
    step so callers (e.g. Streamlit) can show live progress.

    Returns a summary dict with counts and any errors encountered.
    """
    database.init_db()
    scan_id = database.start_scan()

    def report(message: str):
        if progress_callback:
            progress_callback(message)

    errors = []
    all_results = {}

    # Capture prior threat scores before this scan overwrites them.
    prior_scores = database.get_latest_threat_scores()

    for competitor in COMPETITORS:
        report(f"=== {competitor} ===")

        try:
            website_changes = _scan_website(competitor, report)
        except Exception as exc:
            errors.append(f"{competitor}: website scan failed ({exc})")
            website_changes = []

        try:
            product_changes = _scan_product_updates(competitor, report)
        except Exception as exc:
            errors.append(f"{competitor}: product updates scan failed ({exc})")
            product_changes = []
        website_changes = website_changes + product_changes

        try:
            _scan_social(competitor, report)
        except Exception as exc:
            errors.append(f"{competitor}: social scan failed ({exc})")

        try:
            _scan_offers(competitor, report)
        except Exception as exc:
            errors.append(f"{competitor}: offers scan failed ({exc})")

        try:
            sentiment = _scan_reviews(competitor, report)
        except Exception as exc:
            errors.append(f"{competitor}: review scan crashed ({exc})")
            report(f"  [Reviews] Unexpected crash: {exc}")
            sentiment = {
                "sentiment": "neutral", "severity_score": 5.0, "themes": [],
                "top_complaints": [], "top_praise": [],
                "moneris_opportunity": "Review scan crashed unexpectedly.",
            }

        try:
            news = _scan_news(competitor, report)
        except Exception as exc:
            errors.append(f"{competitor}: news analysis failed ({exc})")
            news = []

        threat_score, components = _compute_threat_score(competitor, website_changes, sentiment, news)

        prior = prior_scores.get(competitor)
        prior_score_value = prior["threat_score"] if prior else None

        signals_summary = _build_signals_summary(competitor, website_changes, sentiment, news)

        try:
            reason = explain_threat_score_change(competitor, prior_score_value, threat_score, signals_summary)
        except Exception as exc:
            errors.append(f"{competitor}: threat score explanation failed ({exc})")
            reason = "Threat score updated; explanation unavailable due to an analysis error."

        database.insert_threat_score(
            competitor=competitor,
            threat_score=threat_score,
            review_component=components["review_component"],
            news_component=components["news_component"],
            feature_velocity_component=components["feature_velocity_component"],
            smb_relevance_component=components["smb_relevance_component"],
            reason=reason,
        )

        report(f"  [Threat Score] {competitor}: {threat_score}/10 - {reason}")

        all_results[competitor] = {
            "website_changes": website_changes,
            "sentiment": sentiment,
            "news": news,
            "threat_score": threat_score,
        }

    report("=== Generating Moneris comparison card ===")
    try:
        context_summary = _build_comparison_context(all_results)
        card = generate_comparison_card(list(COMPETITORS.keys()), context_summary)
        database.insert_comparison_card(card["comparison"], card["top_threats"], card["top_advantages"])
        report("  Comparison card generated.")
    except Exception as exc:
        errors.append(f"Comparison card generation failed: {exc}")

    status = "completed" if not errors else "completed_with_errors"
    details = "; ".join(errors) if errors else None
    database.finish_scan(scan_id, status, details)

    total_changes = sum(len(r["website_changes"]) for r in all_results.values())
    total_news = sum(len(r["news"]) for r in all_results.values())

    return {
        "competitors_scanned": len(all_results),
        "website_changes_found": total_changes,
        "news_articles_found": total_news,
        "errors": errors,
    }
