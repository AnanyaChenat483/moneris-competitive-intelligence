"""Central configuration for the Competitive Intelligence Monitor."""

import os

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "monitor.db")

# ---------------------------------------------------------------------------
# Competitors and the pages we monitor for each one (Layer 1: website)
# ---------------------------------------------------------------------------
COMPETITORS = {
    "Stripe": {
        "Pricing": "https://stripe.com/en-ca/pricing",
        "Product": "https://stripe.com/en-ca/payments",
    },
    "Square": {
        "Pricing": "https://squareup.com/ca/en/payments",
        "Product": "https://squareup.com/ca/en/point-of-sale",
    },
    "PayPal": {
        "Pricing": "https://www.paypal.com/ca/business/paypal-business-fees",
        "Product": "https://www.paypal.com/ca/business",
    },
    "Shopify Payments": {
        "Pricing": "https://www.shopify.com/ca/pricing",
        "Product": "https://www.shopify.com/ca/payments",
    },
    "Helcim": {
        "Pricing": "https://www.helcim.com/pricing/",
        "Product": "https://www.helcim.com/",
    },
    "Nuvei": {
        "Pricing": "https://www.nuvei.com/",
        "Product": "https://www.nuvei.com/platform",
    },
}

# ---------------------------------------------------------------------------
# Scraping configuration
# ---------------------------------------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20  # seconds

# Which tags/text we treat as "headings" when extracting page content
HEADING_TAGS = ["h1", "h2", "h3"]

# Keywords used to identify pricing-related text on a page
PRICING_KEYWORDS = [
    "$", "€", "£",
    "/mo", "/month", "/yr", "/year",
    "per month", "per year", "per transaction",
    "%", "fee", "fees", "rate", "rates",
    "pricing", "price", "plan", "plans",
    "subscription", "free trial", "no monthly fee",
    "interchange", "flat rate",
]

# Bounds used when extracting feature/list text
FEATURE_TEXT_MIN_LEN = 3
FEATURE_TEXT_MAX_LEN = 200
PRICING_TEXT_MAX_LEN = 200

# Allowed values for website-change classification
CHANGE_TYPES = ["pricing", "feature", "policy", "UX"]
REVENUE_SENSITIVITY_LEVELS = ["high", "medium", "low"]
SEGMENTS_AFFECTED = ["SMB", "enterprise", "developers"]

# ---------------------------------------------------------------------------
# Layer 2: Customer reviews (Google Play Store)
# ---------------------------------------------------------------------------
PLAY_STORE_APP_IDS = {
    "Stripe":           "com.stripe.android.dashboard",
    "Square":           "com.squareup",
    "PayPal":           "com.paypal.android.p2pmobile",
    "Shopify Payments": "com.shopify",
    "Helcim":           "com.helcim.helcimmobileapp",
    "Nuvei":            "com.nuvei.android",
}

REVIEW_MAX_PER_COMPETITOR = 20

# ---------------------------------------------------------------------------
# Layer 3: News tracker (Google News RSS)
# ---------------------------------------------------------------------------
NEWS_RSS_URL = "https://news.google.com/rss/search"
NEWS_QUERY_TEMPLATE = "{competitor} payments Canada"
NEWS_MAX_ARTICLES_PER_COMPETITOR = 8

# Source weighting for news credibility
HIGH_VALUE_NEWS_SOURCES = [
    "techcrunch", "reuters", "bloomberg", "globe and mail", "the globe and mail",
    "financial post", "wall street journal", "the wall street journal",
    "cnbc", "the verge", "axios", "forbes",
]

# ---------------------------------------------------------------------------
# Feature 1: Moneris comparison card
# ---------------------------------------------------------------------------
COMPARISON_DIMENSIONS = [
    "Distribution model",
    "Developer experience",
    "SMB onboarding speed",
    "POS ecosystem strength",
    "Ecommerce strength",
    "Pricing transparency",
    "Canadian market presence",
]

# ---------------------------------------------------------------------------
# Feature 2: Threat scoring engine
# ---------------------------------------------------------------------------
# Weighted average components (must sum to 1.0)
THREAT_WEIGHTS = {
    "review_sentiment": 0.30,
    "news_momentum": 0.25,
    "feature_velocity": 0.20,
    "smb_relevance": 0.25,
}

# Static SMB-relevance rating (1-10) reflecting how directly each competitor
# competes with Moneris for small-to-medium business merchants.
SMB_RELEVANCE = {
    "Stripe": 8,
    "Square": 9,
    "PayPal": 7,
    "Shopify Payments": 8,
    "Helcim": 7,
    "Nuvei": 5,
}

# ---------------------------------------------------------------------------
# Target company context
# ---------------------------------------------------------------------------
TARGET_COMPANY = "Moneris"
TARGET_COMPANY_CONTEXT = (
    "Moneris is a leading Canadian payment processor, jointly owned by RBC and "
    "BMO, with a strong small-to-medium business (SMB) focus, a wide physical "
    "presence across Canada, a strong point-of-sale (POS) hardware ecosystem, "
    "and pricing models built around interchange-plus and blended rates. "
    "Moneris competes with global payment processors and merchant acquirers - "
    "Stripe, Square, PayPal, Shopify Payments, Helcim, and Nuvei - particularly "
    "for SMB merchants, online/e-commerce payments, in-person point-of-sale, "
    "developer-friendly payment integrations, and transparent pricing in the "
    "Canadian market."
)

# ---------------------------------------------------------------------------
# Claude model used for all analysis
# ---------------------------------------------------------------------------
CLAUDE_MODEL = "claude-opus-4-8"
