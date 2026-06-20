"""Orchestrates all three data layers, AI analysis, threat scoring, and storage."""

import difflib
import hashlib

import database
from analyzer import (
    analyze_news_batch,
    analyze_review_sentiment,
    analyze_website_change,
    explain_threat_score_change,
    generate_comparison_card,
)
from config import COMPETITORS, SMB_RELEVANCE, THREAT_WEIGHTS
from news_client import NewsError, fetch_news_for_competitor
from play_reviews import get_reviews_for_competitor
from scraper import ScrapeError, content_to_text, scrape_page

FEATURE_VELOCITY_BASELINE = 2.0  # used when no website changes detected this scan
NEWS_MOMENTUM_BASELINE = 3.0  # used when no news articles are available this scan


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
