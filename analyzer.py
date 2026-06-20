"""Claude-powered analysis for all three data layers plus synthesis features."""

import json
import os

import anthropic
from dotenv import load_dotenv

from config import (
    CLAUDE_MODEL,
    COMPARISON_DIMENSIONS,
    TARGET_COMPANY,
    TARGET_COMPANY_CONTEXT,
)

load_dotenv()


def get_client() -> anthropic.Anthropic:
    """Return an Anthropic client configured from the ANTHROPIC_API_KEY env var."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
        )
    return anthropic.Anthropic(api_key=api_key)


def _create(schema: dict, prompt: str, max_tokens: int = 1500) -> dict:
    """Call Claude with a JSON-schema-constrained response and return parsed JSON."""
    client = get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": schema,
            }
        },
    )
    for block in response.content:
        if block.type == "text":
            return json.loads(block.text)
    raise RuntimeError("Claude response did not contain a text block.")


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Layer 1: Website change analysis
# ---------------------------------------------------------------------------

_WEBSITE_CHANGE_SCHEMA = {
    "type": "object",
    "properties": {
        "change_type": {
            "type": "string",
            "enum": ["pricing", "feature", "policy", "UX"],
            "description": "The category that best describes this change.",
        },
        "description": {
            "type": "string",
            "description": "A concise, plain-English summary (1-3 sentences) of what changed on the page.",
        },
        "customer_impact_score": {
            "type": "integer",
            "description": (
                "How much this change matters to customers evaluating payment "
                "providers, on a scale of 1 (negligible) to 10 (major). Must be "
                "an integer between 1 and 10 inclusive."
            ),
        },
        "revenue_sensitivity": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "How directly this change could affect Moneris's revenue if merchants react to it.",
        },
        "segment_affected": {
            "type": "string",
            "enum": ["SMB", "enterprise", "developers"],
            "description": "The customer segment most affected by this change.",
        },
    },
    "required": ["change_type", "description", "customer_impact_score", "revenue_sensitivity", "segment_affected"],
    "additionalProperties": False,
}


def analyze_website_change(competitor: str, page_type: str, url: str, old_text: str,
                             new_text: str, diff_text: str) -> dict:
    """Classify a detected website change and score its customer impact."""
    prompt = f"""You are a competitive intelligence analyst for {TARGET_COMPANY}.

About {TARGET_COMPANY}:
{TARGET_COMPANY_CONTEXT}

A competitor's webpage has changed.

Competitor: {competitor}
Page type: {page_type}
URL: {url}

PREVIOUS CONTENT:
---
{old_text}
---

NEW CONTENT:
---
{new_text}
---

DIFF (lines starting with "-" were removed, lines starting with "+" were added):
---
{diff_text}
---

Classify this change and assess its significance for {TARGET_COMPANY}."""

    result = _create(_WEBSITE_CHANGE_SCHEMA, prompt)
    result["customer_impact_score"] = int(_clamp(result["customer_impact_score"], 1, 10))
    return result


# ---------------------------------------------------------------------------
# Layer 2: Customer review sentiment analysis (Google Play Store)
# ---------------------------------------------------------------------------

_REVIEW_SENTIMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "sentiment": {
            "type": "string",
            "enum": ["negative", "neutral", "positive"],
            "description": "Overall sentiment of the app reviews toward this competitor.",
        },
        "themes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Short recurring themes, e.g. 'slow payouts', 'poor support', 'app crashes'.",
        },
        "severity_score": {
            "type": "number",
            "description": (
                "Competitive threat score from 1 to 10: 1 = competitor has very happy "
                "customers (strong threat to Moneris), 10 = widespread complaints "
                "(clear opening for Moneris to win those customers)."
            ),
        },
        "top_complaints": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The most significant recurring complaints, as short phrases.",
        },
        "top_praise": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The most significant positive recurring comments, as short phrases.",
        },
        "moneris_opportunity": {
            "type": "string",
            "description": f"One sentence on what this review sentiment means as a specific opportunity for {TARGET_COMPANY}.",
        },
    },
    "required": ["sentiment", "themes", "severity_score", "top_complaints", "top_praise", "moneris_opportunity"],
    "additionalProperties": False,
}


def analyze_review_sentiment(competitor: str, reviews: list[dict]) -> dict:
    """Analyze Google Play Store reviews for a competitor and surface Moneris opportunities."""
    if not reviews:
        return {
            "sentiment": "neutral",
            "themes": [],
            "severity_score": 5.0,
            "top_complaints": [],
            "top_praise": [],
            "moneris_opportunity": "No app reviews were found for this competitor in this scan.",
        }

    reviews_text = "\n---\n".join(
        f"[{r['rating']}/5 stars | {r['date']}]\n{r['body']}"
        for r in reviews
        if r.get("body")
    )

    prompt = f"""You are a competitive intelligence analyst for {TARGET_COMPANY}.

About {TARGET_COMPANY}:
{TARGET_COMPANY_CONTEXT}

Below are real Google Play Store app reviews of {competitor}'s payment app, showing
star rating (out of 5), date, and review text.

REVIEWS:
---
{reviews_text}
---

Analyze the overall sentiment toward {competitor} expressed in these reviews, identify
recurring themes (both positive and negative), extract the most important complaints
and praise, and assess what this means as a competitive opportunity for {TARGET_COMPANY}.

severity_score scale: 1 = {competitor} has very happy customers (strong competitive threat),
10 = customers are very unhappy (clear opening for {TARGET_COMPANY} to win them)."""

    result = _create(_REVIEW_SENTIMENT_SCHEMA, prompt)
    result["severity_score"] = round(float(_clamp(result["severity_score"], 1, 10)), 1)
    return result


# ---------------------------------------------------------------------------
# Layer 3: News article classification
# ---------------------------------------------------------------------------

_NEWS_BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "articles": {
            "type": "array",
            "description": "One classification per input article, in the same order as given.",
            "items": {
                "type": "object",
                "properties": {
                    "impact_type": {
                        "type": "string",
                        "enum": ["pricing_change", "product_launch", "policy_change", "funding", "partnership", "other"],
                    },
                    "relevance_to_moneris": {
                        "type": "integer",
                        "description": (
                            "How relevant this article is to Moneris's competitive position, "
                            "on a scale of 1 (irrelevant) to 10 (highly relevant). Must be an "
                            "integer between 1 and 10 inclusive."
                        ),
                    },
                    "market_impact": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "summary": {
                        "type": "string",
                        "description": "A one-line summary of the article.",
                    },
                },
                "required": ["impact_type", "relevance_to_moneris", "market_impact", "summary"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["articles"],
    "additionalProperties": False,
}


def analyze_news_batch(competitor: str, articles: list[dict]) -> list[dict]:
    """Classify a batch of news headlines about a competitor in a single call."""
    if not articles:
        return []

    articles_text = "\n".join(
        f"{i + 1}. \"{a['headline']}\" - source: {a['source']} ({a['source_weight']}-credibility), published: {a['published_at']}"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are a competitive intelligence analyst for {TARGET_COMPANY}.

About {TARGET_COMPANY}:
{TARGET_COMPANY_CONTEXT}

Below are {len(articles)} recent news headlines about {competitor}, a payments
competitor. Classify EACH article. Return exactly {len(articles)} classifications,
in the same order as listed.

ARTICLES:
{articles_text}"""

    result = _create(_NEWS_BATCH_SCHEMA, prompt, max_tokens=2000)
    classifications = result.get("articles", [])

    # Defensive: pad/truncate to match input length so callers can zip safely.
    while len(classifications) < len(articles):
        classifications.append({
            "impact_type": "other",
            "relevance_to_moneris": 1,
            "market_impact": "low",
            "summary": "",
        })
    classifications = classifications[:len(articles)]

    for c in classifications:
        c["relevance_to_moneris"] = int(_clamp(c["relevance_to_moneris"], 1, 10))

    return classifications


# ---------------------------------------------------------------------------
# Feature 1: Moneris comparison card
# ---------------------------------------------------------------------------

_COMPARISON_SCHEMA = {
    "type": "object",
    "properties": {
        "competitor_comparisons": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "competitor": {"type": "string"},
                    "dimensions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "dimension": {"type": "string"},
                                "rating": {
                                    "type": "string",
                                    "enum": ["green", "yellow", "red"],
                                    "description": (
                                        f"green = {TARGET_COMPANY} has a clear advantage, "
                                        f"yellow = roughly comparable, "
                                        f"red = the competitor has the advantage."
                                    ),
                                },
                                "note": {"type": "string", "description": "One short sentence justifying the rating."},
                            },
                            "required": ["dimension", "rating", "note"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["competitor", "dimensions"],
                "additionalProperties": False,
            },
        },
        "top_threats": {
            "type": "array",
            "items": {"type": "string"},
            "description": f"The top 3 threats to {TARGET_COMPANY} this week, as short sentences.",
        },
        "top_advantages": {
            "type": "array",
            "items": {"type": "string"},
            "description": f"The top 3 {TARGET_COMPANY} advantages to leverage this week, as short sentences.",
        },
    },
    "required": ["competitor_comparisons", "top_threats", "top_advantages"],
    "additionalProperties": False,
}


def generate_comparison_card(competitors: list[str], context_summary: str) -> dict:
    """Generate a Moneris-vs-competitors comparison across COMPARISON_DIMENSIONS.

    Returns a dict with keys: comparison (nested dict competitor -> dimension -> {rating, note}),
    top_threats (list[str]), top_advantages (list[str]).
    """
    dimensions_list = "\n".join(f"- {d}" for d in COMPARISON_DIMENSIONS)
    competitors_list = ", ".join(competitors)

    prompt = f"""You are a competitive intelligence analyst for {TARGET_COMPANY}.

About {TARGET_COMPANY}:
{TARGET_COMPANY_CONTEXT}

Competitors to compare against {TARGET_COMPANY}: {competitors_list}

Dimensions to rate {TARGET_COMPANY} against each competitor on:
{dimensions_list}

For each competitor, rate {TARGET_COMPANY} on each dimension as:
- "green" if {TARGET_COMPANY} has a clear advantage
- "yellow" if roughly comparable
- "red" if the competitor has the advantage

Recent intelligence gathered this week (website changes, app review sentiment, and news):
---
{context_summary}
---

Provide a rating and one-sentence note for every (competitor, dimension) pair, then
summarize the top 3 threats to {TARGET_COMPANY} this week and the top 3 {TARGET_COMPANY}
advantages to leverage this week."""

    result = _create(_COMPARISON_SCHEMA, prompt, max_tokens=4000)

    comparison = {}
    for entry in result.get("competitor_comparisons", []):
        comp_name = entry.get("competitor")
        comparison[comp_name] = {
            dim["dimension"]: {"rating": dim["rating"], "note": dim["note"]}
            for dim in entry.get("dimensions", [])
        }

    return {
        "comparison": comparison,
        "top_threats": result.get("top_threats", []),
        "top_advantages": result.get("top_advantages", []),
    }


# ---------------------------------------------------------------------------
# Feature 2/3: Threat score attribution
# ---------------------------------------------------------------------------

_THREAT_REASON_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {
            "type": "string",
            "description": (
                "One short sentence explaining why this competitor's threat score "
                "changed (or stayed stable) this scan, referencing the most "
                "significant new signal."
            ),
        },
    },
    "required": ["reason"],
    "additionalProperties": False,
}


def explain_threat_score_change(competitor: str, prior_score, new_score: float,
                                  signals_summary: str) -> str:
    """Ask Claude for a one-sentence attribution of why a threat score changed."""
    if prior_score is None:
        delta_text = f"This is the first recorded threat score for {competitor}: {new_score:.1f}/10."
    else:
        delta = new_score - prior_score
        delta_text = (
            f"{competitor}'s threat score moved from {prior_score:.1f} to {new_score:.1f} "
            f"({'+' if delta >= 0 else ''}{delta:.1f})."
        )

    prompt = f"""You are a competitive intelligence analyst for {TARGET_COMPANY}.

{delta_text}

New signals gathered this scan for {competitor}:
---
{signals_summary}
---

In one short sentence, explain why the threat score changed (or stayed about the
same), referencing the most significant new signal. Example style: "Stripe +1.2
this week due to new customer review complaints about fee increases." """

    result = _create(_THREAT_REASON_SCHEMA, prompt, max_tokens=300)
    return result["reason"]
