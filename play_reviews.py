"""Google Play Store review fetcher.

Uses the google-play-scraper package, which calls Google's internal Play Store
batch API — no browser, no API key, works from any IP.
"""

from google_play_scraper import Sort, reviews as gp_reviews

from config import PLAY_STORE_APP_IDS, REVIEW_MAX_PER_COMPETITOR


def get_reviews_for_competitor(competitor: str, progress_callback=None) -> list[dict]:
    """Fetch the most recent Play Store reviews for a competitor's app.

    Returns a list of dicts: {id, source, body, rating, date, url}.
    Returns [] if the app ID is unknown or the fetch fails.
    """
    def log(msg: str):
        if progress_callback:
            progress_callback(msg)

    app_id = PLAY_STORE_APP_IDS.get(competitor)
    if not app_id:
        log(f"  [Reviews] No Play Store app ID configured for {competitor}")
        return []

    app_url = f"https://play.google.com/store/apps/details?id={app_id}"
    log(f"  [Reviews] Fetching Play Store reviews for {competitor} ({app_id})")

    try:
        result, _ = gp_reviews(
            app_id,
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=REVIEW_MAX_PER_COMPETITOR,
            filter_score_with=None,  # all star ratings
        )
    except Exception as exc:
        log(f"    Play Store fetch failed: {exc}")
        return []

    reviews = []
    for r in result:
        body = (r.get("content") or "").strip()
        if not body:
            continue
        date_str = ""
        if r.get("at"):
            try:
                date_str = r["at"].strftime("%Y-%m-%d")
            except Exception:
                date_str = str(r["at"])[:10]
        reviews.append({
            "id": r.get("reviewId", f"gp_{app_id}_{len(reviews)}"),
            "source": "Google Play",
            "body": body[:600],
            "rating": int(r.get("score") or 0),
            "date": date_str,
            "url": app_url,
        })

    log(f"    Play Store: {len(reviews)} review(s) fetched")
    return reviews
