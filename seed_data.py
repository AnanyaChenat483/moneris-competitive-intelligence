"""Seed data: real 2023-2024 competitive events used to bootstrap the dashboard.

These give the Trends tab a historical baseline before the first live scan,
and populate Tab 1's context with known prior competitive moves.
"""

import database
from config import SMB_RELEVANCE

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
]


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
