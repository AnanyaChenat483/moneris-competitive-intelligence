"""Central configuration for Moneris Product & Program Competitive Insights."""

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
# Layer 1c: Social channels — LinkedIn and YouTube presence per competitor
# ---------------------------------------------------------------------------
# LinkedIn has no public RSS feed for company pages (confirmed: the standard
# "…/posts/rss" pattern just returns the normal SPA HTML shell, not a feed),
# and unauthenticated requests to a company page only return the gated
# "About" overview, never the post feed. Google News scoped to
# site:linkedin.com/posts is used as the proxy signal instead — noisier
# (personal employee posts get mixed in with company content) but real and
# accessible; analyze_social_intelligence is prompted to filter for
# official/campaign-relevant content specifically.
#
# YouTube channel entries store a resolved channel_id, NOT the @handle —
# the legacy `?user=` RSS shortcut is unsafe: `user=Stripe` silently
# resolved to an unrelated channel (old, unconnected music uploads from
# 2012) rather than Stripe's real channel. Every channel_id below was
# resolved from the live @handle page's canonical link, cross-checked
# against a web search for the competitor's official channel, and its feed
# content verified (title and/or recent video titles genuinely match the
# competitor) before being added. This caught two real traps: a batch of
# plausible-looking IDs proposed for Stripe/Square/PayPal/Shopify all
# 404'd (fabricated, despite matching the correct format/length), and
# @heartland — the first hit for "Heartland" — turned out to be the CBC TV
# drama series, not Heartland Payment Systems.
SOCIAL_PAGE_TYPE = "social_intelligence"

SOCIAL_PAGES = {
    "Stripe": {
        "linkedin_query": "Stripe",
        "youtube_channel_id": "UCM1guA1E-RHLO2OyfQPOkEQ",  # @stripe
    },
    "Square": {
        "linkedin_query": '"Square" payments',
        "youtube_channel_id": "UC8XWdXApGfNHTHSm1P9hLEQ",  # @Square
    },
    "PayPal": {
        "linkedin_query": "PayPal",
        "youtube_channel_id": "UCXe1qKfGweMKTnmRrMw9yOg",  # @PayPal
    },
    "Shopify Payments": {
        "linkedin_query": "Shopify",
        "youtube_channel_id": "UCIv38OrggTu3vNkCAo96-CQ",  # @shopify
    },
    # @helcim resolves to the correct channel (confirmed via web search and
    # its videos, e.g. "What Is Helcim & How Does It Work?") but the feed
    # endpoint itself returns 404/500 on every attempt — a channel-side
    # YouTube quirk, not a wrong ID. Included anyway since the ID is
    # correct; fetch_youtube_uploads degrades gracefully (empty result +
    # logged error) whenever the feed is unavailable.
    "Helcim": {
        "linkedin_query": "Helcim payments",
        "youtube_channel_id": "UCeJRrwN3W5sCynCqHB9HF6w",  # @helcim
    },
    "Nuvei": {
        "linkedin_query": "Nuvei",
        "youtube_channel_id": "UCaSOnJ63SP7STlQQlXAjyNw",  # @nuvei
    },
    # @clover is confirmed genuine (matches Clover POS branded content:
    # "Clover Tour for Retail", "Meet Clover Station Duo", etc.) but its
    # feed intermittently 500s — same graceful-degradation handling as
    # Helcim covers this.
    "Clover": {
        "linkedin_query": '"Clover" point of sale payments',
        "youtube_channel_id": "UChBLcixjZLF7u_Xi3t9qBPA",  # @clover
    },
    # No youtube_channel_id: every handle guess for Global Payments/Heartland
    # either 404'd or (for @heartland specifically) resolved to an unrelated
    # channel — the CBC TV drama "Heartland", not Heartland Payment Systems.
    # No genuine official channel was found. LinkedIn-only for this competitor.
    "Global Payments": {
        "linkedin_query": "Global Payments Canada",
    },
}

# The five Claude-generated fields for each Social Channels card.
SOCIAL_CAMPAIGN_FOCUS_OPTIONS = [
    "Product launch",
    "Merchant acquisition",
    "Brand awareness",
    "Thought leadership",
]
SOCIAL_TONE_SHIFT_OPTIONS = ["More aggressive", "Stable", "Retreating"]

# ---------------------------------------------------------------------------
# Layer 1d: Offers & promotions pages
# ---------------------------------------------------------------------------
# Every URL below was tested for real, accessible content before being
# added. Several of the specifically-requested URLs (Stripe's /campaigns,
# Square's /offers, PayPal's /offers and /promotions, Nuvei's /pricing) 404
# or return an empty JS shell — those competitors fall back to their
# richest available pricing/promo-adjacent page instead, documented below.
# Helcim is excluded entirely: helcim.com (every path, confirmed again
# including /pricing/) returns a 403 Cloudflare block, same issue already
# documented for the main Helcim entry in COMPETITORS.
OFFERS_PAGE_TYPE = "offers_promotions"

OFFERS_PAGES = {
    # /campaigns 404s and Stripe has no dedicated promotions page; its
    # pricing page is the only place volume-discount-style offers appear.
    "Stripe": {
        "Pricing": "https://stripe.com/en-ca/pricing",
    },
    # /offers 404s (empty); /hardware is Square's real promo-adjacent page
    # (bundle pricing, free-trial-style hardware offers).
    "Square": {
        "Hardware": "https://squareup.com/ca/en/hardware",
    },
    # /offers returns 200 but is an empty JS shell (16 words); no working
    # dedicated offers/promotions page was found, so this reuses the same
    # fee page already tracked as Pricing in COMPETITORS — acceptable since
    # it feeds a distinct offer-specific classification, not a duplicate view.
    "PayPal": {
        "Merchant fees": "https://www.paypal.com/ca/business/paypal-business-fees",
    },
    "Shopify Payments": {
        "Free trial": "https://www.shopify.com/ca/free-trial",
    },
    # /pricing 404s; no dedicated offers page found. Reuses the existing
    # Product page (already tracked in COMPETITORS) as the closest available
    # promo-adjacent content.
    "Nuvei": {
        "Payment solution": "https://www.nuvei.com/payment-solution",
    },
    "Clover": {
        "Pricing": "https://www.clover.com/ca/en/pricing",
    },
    "Global Payments": {
        "Pricing": "https://www.heartland.us/pricing",
    },
}

OFFER_TYPES = ["free_trial", "hardware_discount", "fee_waiver", "cashback", "bundle", "rate_reduction"]
OFFER_TARGET_SEGMENTS = ["SMB", "LAKA", "New merchants", "Existing merchants"]
OFFER_AGGRESSIVENESS_LEVELS = ["High", "Medium", "Low"]
OFFER_DURATIONS = ["Limited time", "Ongoing"]
OFFER_MONERIS_GAP_VALUES = ["Yes", "No", "Partial"]

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

# Size of the raw candidate pool pulled from Google News RSS before
# deduplication — kept generous so the fuzzy story-grouping in
# news_client.dedupe_articles_by_story has enough real candidates to work
# with (syndicated copies of the same story are often not adjacent in the
# RSS result order).
NEWS_MAX_ARTICLES_PER_COMPETITOR = 20

# Hard cap on new articles processed (classified + inserted) per competitor
# per scan, applied AFTER deduplication — this is the number that actually
# reaches Supabase and the Latest News tab per scan run.
NEWS_MAX_ARTICLES_PER_COMPETITOR_PER_SCAN = 2

# When checking a freshly-fetched candidate against already-stored articles
# for the same competitor (to stop the same story being re-inserted under a
# different URL in a later scan), only compare against articles published
# within this many days — keeps much older, unrelated coverage that happens
# to share similar wording from being treated as "the same story."
NEWS_DEDUP_LOOKBACK_DAYS = 14

# Per-competitor news query overrides (falls back to NEWS_QUERY_TEMPLATE)
# Use these when the default template produces too-generic or redundant queries.
COMPETITOR_NEWS_QUERIES = {
    "Global Payments": "Global Payments Canada",
    "Clover": "Clover POS Canada payments",
}

# Source weighting for news credibility (used for the display "high/low" pill)
HIGH_VALUE_NEWS_SOURCES = [
    "techcrunch", "reuters", "bloomberg", "globe and mail", "the globe and mail",
    "financial post", "wall street journal", "the wall street journal",
    "cnbc", "the verge", "axios", "forbes",
]

# Ordered source credibility ranking used for near-duplicate-story
# deduplication: when multiple articles report the same underlying story,
# only the single highest-credibility source is kept. Lower index = more
# credible; any source not listed here ranks last (lowest credibility).
# Reuters/Bloomberg/WSJ are global top-tier wire/financial press; Globe and
# Mail/Financial Post are top-tier Canadian outlets (explicitly requested,
# in this relative order); Yahoo Finance is a lower-tier aggregator that
# frequently syndicates the same wire story across several of its regional
# editions (the exact duplication pattern this ranking exists to resolve).
NEWS_SOURCE_CREDIBILITY_RANK = [
    "reuters",
    "bloomberg",
    "wall street journal", "the wall street journal",
    "globe and mail", "the globe and mail",
    "financial post",
    "techcrunch",
    "cnbc",
    "the verge",
    "axios",
    "forbes",
    "yahoo finance", "yahoo! finance",
]

# Tuned against a real observed duplicate cluster (three syndicated copies of
# the same "TD Offers Clover Platform in Canada..." story from Yahoo Finance,
# TradingView, and Yahoo! Finance Canada — identical headline text apart from
# the trailing " - Source" suffix) alongside genuinely distinct articles that
# happen to share topical wording (e.g. two independently-written "Clover vs.
# Square" comparison guides from different publishers scored 0.48 sequence /
# 0.55 semantic). The true duplicate cluster scored 1.00/1.00; the highest
# score among real, distinct articles in that same dataset was 0.56/0.55 —
# these thresholds sit with clear margin above that ceiling so genuinely
# different articles don't get merged.
NEWS_DEDUP_SEQUENCE_THRESHOLD = 0.80
NEWS_DEDUP_SEMANTIC_THRESHOLD = 0.75

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
# Weighted average across 6 intelligence signals (must sum to 1.0). Rebalanced
# when Social Channels and Offers & Promotions were added as full data layers:
# the original 4 components were each reduced proportionally to make room for
# the two new ones rather than being reweighted arbitrarily.
THREAT_WEIGHTS = {
    "review_sentiment": 0.20,
    "news_momentum": 0.20,
    "feature_velocity": 0.15,
    "smb_relevance": 0.20,
    "social_activity": 0.15,
    "offers_aggressiveness": 0.10,
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
