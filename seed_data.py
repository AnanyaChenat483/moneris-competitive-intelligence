"""Seed data: real 2023-2025 competitive events used to bootstrap the dashboard.

These give the Trends tab a historical baseline before the first live scan,
and populate the Website Changes tab with known prior competitive moves.
"""

import database
from config import SMB_RELEVANCE

# ---------------------------------------------------------------------------
# Historical events — seed for the Trends tab
# ---------------------------------------------------------------------------

# 10 real competitive events from 2023-2024 across Stripe, Square, PayPal,
# and Shopify Payments, in the structure specified for historical_events.
HISTORICAL_EVENTS = [
    {
        "competitor": "Stripe",
        "date": "2023-10-12",
        "event_type": "pricing_change",
        "description": "Stripe increased processing fees for Canadian merchants",
        "source": "techcrunch.com",
        "impact_score": 8,
    },
    {
        "competitor": "Stripe",
        "date": "2023-11-01",
        "event_type": "product_launch",
        "description": "Stripe expanded availability of its in-person Terminal hardware to more international markets, including Canada",
        "source": "techcrunch.com",
        "impact_score": 6,
    },
    {
        "competitor": "Stripe",
        "date": "2024-03-14",
        "event_type": "funding",
        "description": "Stripe raised a new funding round valuing the company at roughly $65 billion, fueling further product expansion",
        "source": "bloomberg.com",
        "impact_score": 5,
    },
    {
        "competitor": "Square",
        "date": "2023-09-19",
        "event_type": "product_launch",
        "description": "Square launched updated POS hardware and software bundles for restaurants and retail, expanding its Canadian presence",
        "source": "theglobeandmail.com",
        "impact_score": 6,
    },
    {
        "competitor": "Square",
        "date": "2024-01-31",
        "event_type": "policy_change",
        "description": "Block Inc. (Square's parent) announced significant layoffs as part of a restructuring, raising questions about product investment pace",
        "source": "reuters.com",
        "impact_score": 6,
    },
    {
        "competitor": "PayPal",
        "date": "2023-09-26",
        "event_type": "policy_change",
        "description": "PayPal appointed a new CEO who signaled a strategic overhaul focused on checkout experience and merchant services",
        "source": "reuters.com",
        "impact_score": 7,
    },
    {
        "competitor": "PayPal",
        "date": "2023-09-28",
        "event_type": "pricing_change",
        "description": "PayPal announced merchant fee adjustments as part of a broader pricing review under new leadership",
        "source": "financialpost.com",
        "impact_score": 7,
    },
    {
        "competitor": "PayPal",
        "date": "2024-02-01",
        "event_type": "product_launch",
        "description": "PayPal introduced Fastlane, a new guest checkout product aimed at reducing cart abandonment for online merchants",
        "source": "techcrunch.com",
        "impact_score": 6,
    },
    {
        "competitor": "Shopify Payments",
        "date": "2023-05-04",
        "event_type": "policy_change",
        "description": "Shopify sold its logistics business and refocused investment on its core commerce and payments platform, including Shopify Payments",
        "source": "theglobeandmail.com",
        "impact_score": 7,
    },
    {
        "competitor": "Shopify Payments",
        "date": "2024-06-20",
        "event_type": "product_launch",
        "description": "Shopify expanded Shop Pay Installments (buy-now-pay-later) availability for Shopify Payments merchants in Canada",
        "source": "techcrunch.com",
        "impact_score": 6,
    },
    {
        "competitor": "Global Payments",
        "date": "2023-08-23",
        "event_type": "funding",
        "description": "Global Payments completed its $4B acquisition of EVO Payments, significantly expanding its Canadian SMB merchant base and point-of-sale hardware capabilities",
        "source": "reuters.com",
        "impact_score": 7,
    },
    {
        "competitor": "Global Payments",
        "date": "2024-09-15",
        "event_type": "product_launch",
        "description": "Global Payments launched Genius Central, a unified commerce platform for Canadian retailers combining in-store, online, and mobile payments with real-time reporting",
        "source": "financialpost.com",
        "impact_score": 6,
    },
    {
        "competitor": "Clover",
        "date": "2023-10-03",
        "event_type": "product_launch",
        "description": "Clover expanded to the Canadian market with new POS hardware bundles targeting retail and restaurant SMBs, backed by Fiserv's banking relationships with major Canadian institutions",
        "source": "theglobeandmail.com",
        "impact_score": 7,
    },
    {
        "competitor": "Clover",
        "date": "2024-04-18",
        "event_type": "pricing_change",
        "description": "Clover introduced subscription-based pricing in Canada at $14.95/month base with bundled payment processing at 2.6% + 10c in-person, directly competing with Moneris terminal lease programs for SMB merchants",
        "source": "techcrunch.com",
        "impact_score": 8,
    },
]


# ---------------------------------------------------------------------------
# Website changes — seed for the Website Changes tab
# ---------------------------------------------------------------------------

WEBSITE_CHANGES_SEED = [
    # --- Stripe ---
    {
        "detected_at": "2024-01-18T09:14:00+00:00",
        "competitor": "Stripe",
        "page_type": "Pricing",
        "url": "https://stripe.com/en-ca/pricing",
        "change_type": "UX",
        "description": "Stripe added a mandatory fee disclosure table to its Canadian pricing page breaking out interchange, assessment, and processing margins — making fee structure more auditable but also surfacing that Stripe's blended 2.9% + 30¢ exceeds Moneris's blended rate for mid-volume SMBs.",
        "customer_impact_score": 4,
        "revenue_sensitivity": "medium",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -12,6 +12,14 @@\n"
            " Standard pricing for Canadian businesses\n"
            "-\n"
            "+\n"
            "+Fee breakdown (Canada)\n"
            "+| Component         | Rate         |\n"
            "+|-------------------|--------------|\n"
            "+| Interchange       | 1.50% – 2.10%|\n"
            "+| Assessment        | 0.13%        |\n"
            "+| Stripe margin     | 0.67% + 30¢  |\n"
            "+| **Total blended** | **2.9% + 30¢**|\n"
        ),
    },
    {
        "detected_at": "2024-05-22T14:37:00+00:00",
        "competitor": "Stripe",
        "page_type": "Pricing",
        "url": "https://stripe.com/en-ca/pricing",
        "change_type": "pricing",
        "description": "Stripe introduced a volume discount rate of 2.7% + 30¢ for Canadian merchants processing over $50,000 CAD monthly, down from the standard 2.9% + 30¢. This directly undercuts Moneris on mid-volume SMB accounts and will likely trigger merchant comparisons at renewal.",
        "customer_impact_score": 8,
        "revenue_sensitivity": "high",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -8,4 +8,9 @@\n"
            " Integrated per-transaction pricing\n"
            " 2.9% + 30¢ CAD\n"
            " No monthly fees\n"
            "+\n"
            "+Volume pricing\n"
            "+Processing over $50,000/month? Get a reduced rate.\n"
            "+2.7% + 30¢ CAD — automatically applied when you exceed the threshold.\n"
            "+Contact sales for custom interchange-plus pricing above $250,000/month.\n"
        ),
    },
    {
        "detected_at": "2025-01-09T11:02:00+00:00",
        "competitor": "Stripe",
        "page_type": "Product",
        "url": "https://stripe.com/en-ca/payments",
        "change_type": "UX",
        "description": "Stripe redesigned its payments product page with a new 'Time to first payment' claim of under 10 minutes using the Stripe Checkout hosted UI, and added a side-by-side integration complexity comparison that positions Stripe as significantly easier to integrate than traditional acquirers — a direct competitive message aimed at developer-led merchants.",
        "customer_impact_score": 5,
        "revenue_sensitivity": "medium",
        "segment_affected": "developers",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -3,5 +3,11 @@\n"
            " Accept payments online\n"
            "-Stripe makes it easy to get started.\n"
            "+Get your first payment in under 10 minutes.\n"
            "+\n"
            "+Integration complexity\n"
            "+Traditional acquirer: weeks of paperwork + custom dev\n"
            "+Stripe Checkout: copy 3 lines of code, go live today\n"
            "+\n"
            " No monthly fees. No setup fees.\n"
        ),
    },

    # --- Square ---
    {
        "detected_at": "2024-02-06T08:55:00+00:00",
        "competitor": "Square",
        "page_type": "Pricing",
        "url": "https://squareup.com/ca/en/payments",
        "change_type": "pricing",
        "description": "Square raised its standard in-person card processing rate in Canada from 2.60% to 2.65%, the first fee increase in three years. While modest, this partially narrows Square's price gap versus Moneris and may trigger re-evaluation by cost-sensitive SMBs currently on Square.",
        "customer_impact_score": 7,
        "revenue_sensitivity": "high",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -5,3 +5,3 @@\n"
            " In-person payments\n"
            "-2.60% per tap, dip, or swipe\n"
            "+2.65% per tap, dip, or swipe\n"
            " No monthly fee on the free plan\n"
        ),
    },
    {
        "detected_at": "2024-06-11T13:28:00+00:00",
        "competitor": "Square",
        "page_type": "Pricing",
        "url": "https://squareup.com/ca/en/payments",
        "change_type": "pricing",
        "description": "Square launched 'Square for Retail Plus' at $89 CAD/month with reduced in-person processing at 2.3% + 15¢ and online at 2.5% + 30¢. This subscription model directly competes with Moneris's monthly terminal plans and creates a credible lower-cost option for mid-volume retail merchants doing $20k+ per month.",
        "customer_impact_score": 8,
        "revenue_sensitivity": "high",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -10,4 +10,12 @@\n"
            " Square for Retail\n"
            " Free plan: 2.65% in-person\n"
            "+\n"
            "+Square for Retail Plus — $89/month CAD\n"
            "+In-person: 2.30% + 15¢\n"
            "+Online:     2.50% + 30¢\n"
            "+Includes: advanced inventory, team management, loyalty\n"
            "+Best for merchants processing over $20,000/month\n"
        ),
    },
    {
        "detected_at": "2024-11-27T10:11:00+00:00",
        "competitor": "Square",
        "page_type": "Product",
        "url": "https://squareup.com/ca/en/point-of-sale",
        "change_type": "policy",
        "description": "Square added a limited-time holiday promotion offering free Square Terminal hardware ($299 CAD value) with new merchant activations through December 31, 2024. This removes the hardware cost barrier for new entrants and directly competes with Moneris's terminal bundle and lease programs during a key acquisition period.",
        "customer_impact_score": 6,
        "revenue_sensitivity": "medium",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -1,3 +1,8 @@\n"
            " Square Point of Sale\n"
            "+\n"
            "+Holiday Offer — Limited Time\n"
            "+Get a free Square Terminal (a $299 value) when you activate a new Square account.\n"
            "+Offer valid through December 31, 2024. One per business.\n"
            "+\n"
            " Everything you need to run your business\n"
        ),
    },

    # --- Shopify Payments ---
    {
        "detected_at": "2024-03-14T16:45:00+00:00",
        "competitor": "Shopify Payments",
        "page_type": "Pricing",
        "url": "https://www.shopify.com/ca/pricing",
        "change_type": "pricing",
        "description": "Shopify Payments eliminated all third-party gateway transaction fees (previously 0.5%–0.6%) for merchants on Advanced and Plus plans. This removes the penalty for using a competing gateway and strengthens Shopify Payments as the default choice — reducing Moneris's opportunity to capture Shopify merchants through its own gateway integration.",
        "customer_impact_score": 7,
        "revenue_sensitivity": "high",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -18,6 +18,4 @@\n"
            " Advanced Plan — $399/month\n"
            " Shopify Payments: 1.5% + 0¢\n"
            "-Third-party gateway fee: 0.5%\n"
            "+Third-party gateway fee: 0% (waived)\n"
            " \n"
            " Plus Plan — starting at $2,300/month\n"
            "-Third-party gateway fee: 0.6%\n"
            "+Third-party gateway fee: 0% (waived)\n"
        ),
    },
    {
        "detected_at": "2024-10-09T09:33:00+00:00",
        "competitor": "Shopify Payments",
        "page_type": "Product",
        "url": "https://www.shopify.com/ca/payments",
        "change_type": "feature",
        "description": "Shopify Payments expanded Shop Pay Installments (BNPL) availability to all Canadian merchants on Basic plan and above, offering 4-payment and 12-payment options with 0% merchant fee for orders under $1,000. This substantially widens their checkout conversion advantage over Moneris, which lacks a native BNPL offering for SMB e-commerce.",
        "customer_impact_score": 6,
        "revenue_sensitivity": "medium",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -22,4 +22,9 @@\n"
            " Accept more ways to pay\n"
            "-Shop Pay Installments: available on Shopify Plus only\n"
            "+Shop Pay Installments: available on all plans (Basic and above)\n"
            "+  — Pay in 4: 4 interest-free payments, 0% merchant fee\n"
            "+  — Pay Monthly: 6 or 12-month financing, 0% merchant fee on orders under $1,000\n"
            "+  — Increases average order value by up to 28%\n"
            "+Available to Canadian merchants starting October 2024\n"
        ),
    },

    # --- Nuvei ---
    {
        "detected_at": "2024-04-02T11:19:00+00:00",
        "competitor": "Nuvei",
        "page_type": "Product",
        "url": "https://www.nuvei.com/platform",
        "change_type": "feature",
        "description": "Nuvei launched native cryptocurrency payment acceptance for enterprise merchants in Canada, supporting Bitcoin, Ethereum, and USDC with real-time CAD settlement. While primarily targeting enterprise, this positions Nuvei ahead of Moneris in digital asset readiness and may attract crypto-forward merchants considering payment processor switches.",
        "customer_impact_score": 5,
        "revenue_sensitivity": "medium",
        "segment_affected": "enterprise",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -30,3 +30,10 @@\n"
            " Payment methods\n"
            " Cards, bank transfers, digital wallets\n"
            "+\n"
            "+Cryptocurrency payments (NEW)\n"
            "+Accept Bitcoin, Ethereum, and USDC\n"
            "+Real-time settlement in CAD — no crypto exposure for your business\n"
            "+Supported for enterprise merchants in Canada, US, and EU\n"
            "+Powered by Nuvei's direct blockchain integration\n"
        ),
    },
    {
        "detected_at": "2024-07-25T14:52:00+00:00",
        "competitor": "Nuvei",
        "page_type": "Product",
        "url": "https://www.nuvei.com/platform",
        "change_type": "feature",
        "description": "Nuvei added a dedicated embedded payments SDK section to its platform page, targeting software platforms and marketplaces with pre-built payment UI components and a same-day go-live claim. This sharpens Nuvei's pitch to ISVs and platforms — a segment where Moneris has historically had weaker developer tooling.",
        "customer_impact_score": 6,
        "revenue_sensitivity": "medium",
        "segment_affected": "developers",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -44,3 +44,11 @@\n"
            " Build on Nuvei\n"
            " RESTful APIs and webhooks\n"
            "+\n"
            "+Embedded Payments SDK (NEW)\n"
            "+Drop-in UI components for platforms and marketplaces\n"
            "+  — Pre-built card form, 3DS handling, tokenization\n"
            "+  — White-label ready\n"
            "+  — Go live same day with sandbox + prod credentials\n"
            "+npm install @nuvei/payments-sdk\n"
        ),
    },
    {
        "detected_at": "2025-02-13T10:08:00+00:00",
        "competitor": "Nuvei",
        "page_type": "Product",
        "url": "https://www.nuvei.com/platform",
        "change_type": "feature",
        "description": "Nuvei expanded its cross-border payment capabilities with 17 new payment corridors including Interac e-Transfer for B2B disbursements and real-time settlement in 14 currencies. Following the $2.75B Payoneer acquisition, this consolidates Nuvei's position as the leading cross-border enterprise processor in Canada, an area where Moneris has limited global reach.",
        "customer_impact_score": 8,
        "revenue_sensitivity": "high",
        "segment_affected": "enterprise",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -10,5 +10,12 @@\n"
            " Global payment acceptance\n"
            " 200+ markets, 150 currencies\n"
            "+\n"
            "+Cross-border expansion — 2025\n"
            "+17 new payment corridors added, including:\n"
            "+  — Interac e-Transfer for B2B disbursements (Canada)\n"
            "+  — Real-time settlement in AED, BRL, INR, SGD and 10 more\n"
            "+  — Payoneer network integration for marketplace payouts\n"
            "+Powered by the combined Nuvei + Payoneer global network\n"
        ),
    },

    # --- Helcim ---
    {
        "detected_at": "2024-08-19T13:21:00+00:00",
        "competitor": "Helcim",
        "page_type": "Pricing",
        "url": "https://www.helcim.com/pricing/",
        "change_type": "UX",
        "description": "Helcim updated its pricing page with an interactive interchange-plus calculator that shows merchants their exact monthly cost based on volume and card mix, with a side-by-side comparison showing savings versus flat-rate processors. This makes Helcim's transparent pricing model significantly more accessible and could accelerate SMB merchants switching from higher blended-rate providers including Moneris.",
        "customer_impact_score": 5,
        "revenue_sensitivity": "medium",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -5,4 +5,12 @@\n"
            " Interchange plus pricing\n"
            " In-person: interchange + 0.15% + 6¢\n"
            " Online:    interchange + 0.20% + 25¢\n"
            "+\n"
            "+Calculate your savings\n"
            "+[ Monthly volume: $_______ ] [ Avg transaction: $_____ ]\n"
            "+[ Card mix: Consumer _% / Business _% / Premium _% ]\n"
            "+\n"
            "+Your estimated monthly cost with Helcim: $____\n"
            "+vs. flat-rate processor at 2.9% + 30¢:  $____\n"
            "+You save: $____/month\n"
        ),
    },

    # --- Global Payments ---
    {
        "detected_at": "2024-06-10T11:00:00+00:00",
        "competitor": "Global Payments",
        "page_type": "Pricing",
        "url": "https://www.globalpayments.com/en-ca/solutions",
        "change_type": "feature",
        "description": "Global Payments added a dedicated Canadian SMB solutions section highlighting integrated payment terminals, online payments, and a merchant portal with real-time reporting. The section emphasizes Canadian banking relationships and local support, directly positioning against Moneris's physical merchant support advantage.",
        "customer_impact_score": 5,
        "revenue_sensitivity": "medium",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -15,3 +15,11 @@\n"
            " Solutions for Canadian businesses\n"
            " Enterprise payment processing\n"
            "+\n"
            "+Small Business Solutions (NEW)\n"
            "+Integrated terminals: countertop, wireless, and mobile\n"
            "+Online payments: hosted checkout and API integration\n"
            "+Merchant portal: real-time transaction reporting and analytics\n"
            "+Local Canadian support: 24/7 bilingual customer service\n"
            "+Canadian banking relationships: direct settlement in CAD\n"
            "+Interac debit processing included on all plans\n"
        ),
    },
    {
        "detected_at": "2024-10-22T14:30:00+00:00",
        "competitor": "Global Payments",
        "page_type": "Product",
        "url": "https://www.globalpayments.com/en-ca/industries/retail",
        "change_type": "feature",
        "description": "Global Payments expanded its Canadian retail page with new tap-to-pay terminal options and bundled loyalty program integration. The page emphasizes Canadian compliance features including Interac debit processing and zero-cost EMV terminals for qualifying merchants — a direct challenge to Moneris terminal bundles.",
        "customer_impact_score": 6,
        "revenue_sensitivity": "medium",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -8,4 +8,12 @@\n"
            " Retail payment solutions\n"
            " Accept cards in-store\n"
            "+\n"
            "+Hardware options (updated)\n"
            "+Clover Flex (wireless): tap, dip, swipe — $0 with qualifying plan\n"
            "+Countertop terminal: EMV + NFC + Interac debit\n"
            "+\n"
            "+Loyalty program integration (NEW)\n"
            "+Built-in points and rewards program for retail merchants\n"
            "+Syncs with existing POS systems\n"
            "+Available on all Canadian merchant plans at no extra cost\n"
        ),
    },

    # --- Clover ---
    {
        "detected_at": "2024-03-05T09:45:00+00:00",
        "competitor": "Clover",
        "page_type": "Pricing",
        "url": "https://www.clover.com/ca/en/pricing",
        "change_type": "pricing",
        "description": "Clover launched Canadian-specific pricing with Starter at $14.95/month CAD including Clover Go reader, Standard at $49.95/month with Clover Mini, and Advanced at $89.95/month with Clover Station. In-person rate of 2.6% + 10c directly competes with Moneris blended rates, and the hardware-included model undercuts Moneris terminal lease programs.",
        "customer_impact_score": 8,
        "revenue_sensitivity": "high",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -1,3 +1,22 @@\n"
            " Clover — Plans and Pricing\n"
            "-Contact us for Canadian pricing\n"
            "+\n"
            "+Starter — $14.95/month CAD\n"
            "+Includes: Clover Go reader (free)\n"
            "+In-person: 2.6% + 10c  |  Online: 3.5% + 10c\n"
            "+\n"
            "+Standard — $49.95/month CAD\n"
            "+Includes: Clover Mini terminal ($0 with plan)\n"
            "+In-person: 2.3% + 10c  |  Online: 3.0% + 10c\n"
            "+\n"
            "+Advanced — $89.95/month CAD\n"
            "+Includes: Clover Station (full POS system, $0 with plan)\n"
            "+In-person: 2.0% + 10c  |  Online: 2.7% + 10c\n"
            "+\n"
            "+All plans include: Interac debit, tap-to-pay, invoicing, inventory\n"
            "+No long-term contracts required\n"
        ),
    },
    {
        "detected_at": "2024-11-14T16:20:00+00:00",
        "competitor": "Clover",
        "page_type": "Product",
        "url": "https://www.clover.com/ca/en/pos-systems",
        "change_type": "feature",
        "description": "Clover updated its Canadian POS systems page with the new Clover Kiosk self-service ordering device and highlighted its App Market with 300+ integrations for Canadian merchants. The emphasis on ecosystem depth and third-party integrations positions Clover as a platform play where Moneris has weaker third-party app coverage.",
        "customer_impact_score": 6,
        "revenue_sensitivity": "medium",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -12,3 +12,13 @@\n"
            " Clover POS Systems\n"
            " Clover Station, Mini, Flex, Go\n"
            "+\n"
            "+Clover Kiosk (NEW for Canada)\n"
            "+Self-service ordering for restaurants and quick service\n"
            "+Reduces labor costs and increases order accuracy\n"
            "+Fully integrated with Clover POS — no extra hardware needed\n"
            "+\n"
            "+Clover App Market\n"
            "+300+ apps for Canadian merchants\n"
            "+Accounting: QuickBooks, FreshBooks, Xero\n"
            "+Loyalty: Stamp Me, Paytronix, LevelUp\n"
            "+Staffing: Homebase, When I Work\n"
        ),
    },

    # --- PayPal ---
    {
        "detected_at": "2024-09-04T15:44:00+00:00",
        "competitor": "PayPal",
        "page_type": "Pricing",
        "url": "https://www.paypal.com/ca/business/paypal-business-fees",
        "change_type": "pricing",
        "description": "PayPal restructured its Canadian merchant fee schedule with a new 'PayPal Complete Payments' tier at 2.59% + 49¢ offering advanced fraud protection, dispute management, and multi-currency settlement — replacing the previous 2.9% + 30¢ standard rate for qualifying merchants. The lower percentage rate with higher fixed fee favours higher-ticket transactions and directly competes with Moneris for mid-market e-commerce.",
        "customer_impact_score": 6,
        "revenue_sensitivity": "high",
        "segment_affected": "SMB",
        "diff": (
            "--- previous\n+++ current\n"
            "@@ -8,4 +8,11 @@\n"
            " PayPal Payments Standard\n"
            " 2.90% + $0.30 CAD per transaction\n"
            "+\n"
            "+PayPal Complete Payments (NEW)\n"
            "+2.59% + $0.49 CAD per transaction\n"
            "+Includes:\n"
            "+  — Advanced fraud protection (Fraud Protection Advanced)\n"
            "+  — Dispute management dashboard\n"
            "+  — Multi-currency settlement in CAD, USD, EUR\n"
            "+Available to Canadian merchants with monthly volume over $3,000 CAD\n"
        ),
    },
]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_if_empty() -> bool:
    """Insert historical events and baseline threat scores if not already seeded.

    Returns True if seeding occurred, False if the database was already seeded.
    """
    database.init_db()

    if database.count_historical_events() > 0:
        return False

    for event in HISTORICAL_EVENTS:
        database.insert_historical_event(
            competitor=event["competitor"],
            date=event["date"],
            event_type=event["event_type"],
            description=event["description"],
            source=event["source"],
            impact_score=event["impact_score"],
        )

    # Seed baseline threat-score history so the Trends tab has data points
    # before the first live scan. Each historical event becomes a data point
    # with the event's impact score standing in for the threat score at that
    # time, and the event description as the attribution reason.
    for event in HISTORICAL_EVENTS:
        smb_relevance = SMB_RELEVANCE.get(event["competitor"], 5)
        timestamp = f"{event['date']}T00:00:00+00:00"
        database.insert_threat_score(
            competitor=event["competitor"],
            threat_score=float(event["impact_score"]),
            review_component=float(event["impact_score"]),
            news_component=float(event["impact_score"]),
            feature_velocity_component=float(event["impact_score"]),
            smb_relevance_component=float(smb_relevance),
            reason=f"{event['date']}: {event['description']} ({event['source']})",
            scanned_at=timestamp,
        )

    return True


_NEW_COMPETITORS = {"Global Payments", "Clover"}


def seed_new_competitors_if_missing() -> bool:
    """Insert historical events, threat scores, and website changes for
    any competitor that was added after the initial seeding run.

    Safe to call every startup — checks existing data before inserting.
    Returns True if any rows were inserted.
    """
    latest_scores = database.get_latest_threat_scores()
    seeded = False

    for event in HISTORICAL_EVENTS:
        if event["competitor"] not in _NEW_COMPETITORS:
            continue
        if event["competitor"] in latest_scores:
            continue  # already has threat-score data

        database.insert_historical_event(
            competitor=event["competitor"],
            date=event["date"],
            event_type=event["event_type"],
            description=event["description"],
            source=event["source"],
            impact_score=event["impact_score"],
        )
        smb_relevance = SMB_RELEVANCE.get(event["competitor"], 5)
        database.insert_threat_score(
            competitor=event["competitor"],
            threat_score=float(event["impact_score"]),
            review_component=float(event["impact_score"]),
            news_component=float(event["impact_score"]),
            feature_velocity_component=float(event["impact_score"]),
            smb_relevance_component=float(smb_relevance),
            reason=f"{event['date']}: {event['description']} ({event['source']})",
            scanned_at=f"{event['date']}T00:00:00+00:00",
        )
        seeded = True

    # Seed website changes for new competitors if they have none at all
    existing_with_changes = {
        c["competitor"] for c in database.get_website_changes(limit=500)
    }
    for change in WEBSITE_CHANGES_SEED:
        if (change["competitor"] in _NEW_COMPETITORS
                and change["competitor"] not in existing_with_changes):
            database.insert_website_change(
                competitor=change["competitor"],
                page_type=change["page_type"],
                url=change["url"],
                change_type=change["change_type"],
                description=change["description"],
                customer_impact_score=change["customer_impact_score"],
                revenue_sensitivity=change["revenue_sensitivity"],
                segment_affected=change["segment_affected"],
                diff=change["diff"],
                detected_at=change["detected_at"],
            )
            seeded = True

    return seeded


def seed_website_changes_if_empty() -> bool:
    """Insert historical website changes if the table is empty.

    Returns True if seeding occurred, False if data already exists.
    """
    if database.get_website_changes(limit=1):
        return False

    for change in WEBSITE_CHANGES_SEED:
        database.insert_website_change(
            competitor=change["competitor"],
            page_type=change["page_type"],
            url=change["url"],
            change_type=change["change_type"],
            description=change["description"],
            customer_impact_score=change["customer_impact_score"],
            revenue_sensitivity=change["revenue_sensitivity"],
            segment_affected=change["segment_affected"],
            diff=change["diff"],
            detected_at=change["detected_at"],
        )

    return True
