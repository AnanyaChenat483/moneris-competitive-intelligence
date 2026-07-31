"""Central configuration for the Competitive Intelligence Monitor."""

import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Supabase connection
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

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
    # helcim.com blocks all scrapers (Cloudflare 403 on every path and UA).
    # learn.helcim.com is their public knowledge base — server-side rendered,
    # accessible, and meaningful: docs hub (~9k words) + payment tools page
    # (~16k words) will change when Helcim updates features or onboarding.
    "Helcim": {
        "Docs": "https://learn.helcim.com/",
        "Product": "https://learn.helcim.com/docs/helcim-payment-tools",
    },
    "Nuvei": {
        "Pricing": "https://www.nuvei.com/",
        "Product": "https://www.nuvei.com/payment-solution",
    },
    # globalpayments.com is fully behind Cloudflare (403 on every path).
    # Heartland Payment Systems (heartland.us) is a Global Payments brand;
    # both pages return 200 with rich content (1400-2500 words).
    "Global Payments": {
        "Home": "https://www.heartland.us/",
        "POS": "https://www.heartland.us/products/point-of-sale",
    },
    "Clover": {
        "Pricing": "https://www.clover.com/ca/en/pricing",
    },
}

# ---------------------------------------------------------------------------
# Layer 1b: Product changelog / newsroom / release-notes pages
# ---------------------------------------------------------------------------
# The richest source of product intelligence: changelogs, "shipped" pages,
# roadmaps, and newsrooms announce concrete product moves well before they
# show up on marketing pricing/product pages. Tracked separately from
# COMPETITORS above under page_type PRODUCT_UPDATE_PAGE_TYPE so the dashboard
# can filter on them independently. Every URL below was verified (200 status,
# real server-rendered content) before being added; URLs that returned 403
# (Cloudflare-blocked) or were empty JS shells were left out — see the
# comments per competitor.
PRODUCT_UPDATE_PAGE_TYPE = "product_updates"

PRODUCT_UPDATE_PAGES = {
    "Stripe": {
        "Changelog": "https://stripe.com/blog/changelog",
        "Shipped": "https://stripe.com/shipped",
        "Roadmap": "https://stripe.com/roadmap",
        "Newsroom": "https://stripe.com/newsroom/news",
    },
    "Square": {
        "Newsroom": "https://squareup.com/ca/en/press",
        "Developer changelog": "https://developer.squareup.com/blog",
        "What's new": "https://squareup.com/ca/en/whats-new",
    },
    # newsroom.paypal.com does not resolve (no such host) and the requested
    # business-blog URL (paypal.com/ca/webapps/mpp/blog) 404s. PayPal's real
    # newsroom lives on a different subdomain (found via search); a Canada
    # edition replaces the dead "business blog" link.
    "PayPal": {
        "Newsroom": "https://newsroom.paypal-corp.com/news",
        "Newsroom (Canada)": "https://newsroom.ca.paypal-corp.com/",
    },
    "Shopify Payments": {
        "Changelog": "https://changelog.shopify.com",
        "Blog": "https://www.shopify.com/ca/blog",
        "Engineering blog": "https://shopify.engineering",
    },
    # helcim.com (main domain, including /blog and /whats-new) returns a 403
    # Cloudflare block for every path and user agent — same issue already
    # documented for the main Helcim entry above. No product-update pages
    # available for Helcim.
    "Nuvei": {
        "Newsroom": "https://www.nuvei.com/post-category/newsroom",
        "Blog": "https://www.nuvei.com/post-category/blog",
    },
    # blog.clover.com moved here from COMPETITORS above — it's changelog-style
    # content and belongs in the product intelligence category. Clover's
    # App Market page (clover.com/app-market) is a JS-rendered shell with ~8
    # words of static content, same issue as other clover.com marketing
    # pages — excluded.
    "Clover": {
        "Blog": "https://blog.clover.com/",
    },
    # heartland.us/news and every plausible newsroom path (/newsroom, /press,
    # /press-releases, /about/newsroom, etc.) 404. Global Payments' press
    # releases live on the Cloudflare-blocked corporate site. Only the blog
    # is available.
    "Global Payments": {
        "Blog": "https://www.heartland.us/blog",
    },
}

# The Moneris product areas a product-update change can be mapped to (Feature
# 5: Product Intelligence). "No Moneris equivalent (gap)" is used both for
# categories Moneris has no product for (BNPL, stablecoins/crypto, embedded
# finance) and for anything else that doesn't fit the other areas.
MONERIS_GAP_LABEL = "No Moneris equivalent (gap)"

MONERIS_PRODUCT_AREAS = [
    "Moneris Go Terminal / Go Retail POS / Go Restaurant POS",
    "Moneris Online / Total Commerce",
    "Moneris MCP Server / Developer tools",
    "PAYD / Tap to Pay",
    "Moneris Data & Insights",
    "Moneris Payment Facilitation",
    MONERIS_GAP_LABEL,
]

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
SEGMENTS_AFFECTED = ["SMB", "LAKA", "Partners", "Developers"]

# ---------------------------------------------------------------------------
# Layer 2: Customer reviews (Google Play Store)
# ---------------------------------------------------------------------------
PLAY_STORE_APP_IDS = {
    "Stripe":           "com.stripe.android.dashboard",
    "Square":           "com.squareup",
    "PayPal":           "com.paypal.android.p2pmobile",
    "Shopify Payments": "com.shopify",
    "Helcim":           "com.helcim.helcim_payments_app_android",
    "Global Payments":  "com.apriva.mobile.globalpayments.mobilepay",
    "Clover":           "clover.companion.app",
    # Nuvei has no Google Play app — omitted so the UI shows "No app available"
}

REVIEW_MAX_PER_COMPETITOR = 20

# ---------------------------------------------------------------------------
# Layer 3: News tracker (Google News RSS)
# ---------------------------------------------------------------------------
NEWS_RSS_URL = "https://news.google.com/rss/search"
NEWS_QUERY_TEMPLATE = "{competitor} payments Canada"
NEWS_MAX_ARTICLES_PER_COMPETITOR = 8

# Per-competitor news query overrides (falls back to NEWS_QUERY_TEMPLATE)
# Use these when the default template produces too-generic or redundant queries.
COMPETITOR_NEWS_QUERIES = {
    "Global Payments": "Global Payments Canada",
    "Clover": "Clover POS Canada payments",
}

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
    "Global Payments": 6,
    "Clover": 8,
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
    "Stripe, Square, PayPal, Shopify Payments, Helcim, Nuvei, Global Payments, "
    "and Clover - particularly for SMB merchants, online/e-commerce payments, "
    "in-person point-of-sale, developer-friendly payment integrations, and "
    "transparent pricing in the Canadian market."
)

# ---------------------------------------------------------------------------
# Claude model used for all analysis
# ---------------------------------------------------------------------------
CLAUDE_MODEL = "claude-opus-4-8"
