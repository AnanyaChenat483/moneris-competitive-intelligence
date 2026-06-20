# Moneris Competitive Intelligence Monitor

> An AI-powered competitive intelligence system that tracks, analyzes, and synthesizes signals from six Canadian fintech competitors — automatically, weekly, in one dashboard.

---

## Overview

This system monitors Stripe, Square, PayPal, Shopify Payments, Helcim, and Nuvei across three live data sources — competitor website changes, Google Play Store app reviews, and Google News — and uses Claude AI (Anthropic) to classify signals, score competitive threats, and generate strategic recommendations for Moneris. Every scan produces a ranked threat score per competitor, a cross-dimensional comparison card, and a full audit trail of what changed, when, and why it matters. The result is a single Streamlit dashboard that replaces hours of manual competitive research with an automated weekly intelligence brief.

---

## Why I Built This

Moneris's martech team had no systematic way to track competitor moves in the Canadian payments market — monitoring happened ad hoc, reactively, and inconsistently. I built this to automate that process end-to-end: from raw web scraping and review ingestion, through AI-powered classification, to a polished dashboard that surfaces actionable intelligence without requiring anyone to open a browser. The goal was to make competitive awareness a continuous process, not a quarterly project.

---

## Features

### 🌐 Website Changes
Scrapes pricing and product pages for all six competitors on every scan. Detects content changes via SHA-256 hashing, diffs the old and new versions, and sends the diff to Claude for classification (pricing / feature / policy / UX) and impact scoring (1–10). Only changes scoring 2/10 or above are stored. Near-duplicates within the same day are automatically deduplicated.

### ⭐ Customer Reviews
Fetches the 20 most recent Google Play Store app reviews per competitor using `google-play-scraper` (no API key, no browser required). Claude analyzes the review set for recurring themes, top complaints, top praise, and a severity score (1–10, where 10 = widespread dissatisfaction = strongest Moneris opportunity). Results are stored per scan for trend tracking.

### 📰 Latest News
Queries Google News RSS for each competitor and scores every article for Moneris relevance (1–10) and impact type (pricing change / product launch / policy change / funding / partnership). Articles older than 90 days are filtered out automatically. High-credibility sources (Reuters, Bloomberg, TechCrunch, Globe and Mail, etc.) are flagged for weighting.

### ⚖️ Moneris vs Competitors
After each scan, Claude synthesizes all signals into a cross-competitor comparison card across seven strategic dimensions: Distribution Model, Developer Experience, SMB Onboarding Speed, POS Ecosystem Strength, Ecommerce Strength, Pricing Transparency, and Canadian Market Presence. Each cell is rated green (Moneris advantage) / yellow (comparable) / red (competitor advantage), with a one-sentence reasoning note accessible on hover. The card also surfaces the top three threats and top three Moneris advantages for the week.

### 📈 Trends
Tracks threat scores over time per competitor with a fully dark-themed Altair line chart. Each data point includes a Claude-generated one-sentence explanation of why the score moved. Historical seed data from real market events (2022–2025) provides baseline context from day one. The breakdown table shows every score component with the full attribution text.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Dashboard | [Streamlit](https://streamlit.io) |
| AI Analysis | [Claude API](https://www.anthropic.com) — `claude-opus-4-8` with adaptive thinking |
| Database | [Supabase](https://supabase.com) (PostgreSQL) |
| Web Scraping | `requests` + `BeautifulSoup4` |
| App Reviews | `google-play-scraper` |
| News | Google News RSS (no API key required) |
| Charts | `altair` |
| Data | `pandas` |

---

## How the Threat Score Works

Each competitor receives a composite threat score on a 1–10 scale, computed as a weighted average of four signals captured on every scan:

```
Threat Score =
    App Review Sentiment  × 0.30
  + News Momentum         × 0.25
  + Feature Velocity      × 0.20
  + SMB Relevance         × 0.25
```

| Component | Weight | What it measures |
|---|---|---|
| **App Review Sentiment** | 30% | Severity of customer dissatisfaction in Google Play reviews (higher = more unhappy customers = more Moneris opportunity) |
| **News Momentum** | 25% | Average Moneris-relevance score across news articles fetched this scan |
| **Feature Velocity** | 20% | Average customer impact score of detected website changes |
| **SMB Relevance** | 25% | Static rating of how directly each competitor targets Moneris's SMB core market |

A score of **7–10** signals a competitor making aggressive moves worth immediate attention. **4–6** is watch-list territory. **1–3** indicates low activity or positive differentiation for Moneris.

---

## Screenshots

> _Add screenshots here_

---

## Setup

**Requirements:** Python 3.11+, an [Anthropic API key](https://console.anthropic.com/), a free [Supabase](https://supabase.com) project

```bash
# 1. Clone the repository
git clone <repo-url>
cd competitive-monitor

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
.\venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the Supabase tables
#    Open your Supabase project → SQL Editor → paste and run schema.sql

# 5. Add your credentials
cp .env.example .env
# Open .env and set:
#   ANTHROPIC_API_KEY=sk-ant-...
#   SUPABASE_URL=https://your-project-ref.supabase.co
#   SUPABASE_KEY=your_anon_or_service_role_key

# 6. Run the dashboard
streamlit run app.py
```

The app seeds historical event data automatically on first run. Open `http://localhost:8501`, then click **Run Full Scan** in the sidebar to populate live data.

**Deploying to Streamlit Cloud:** Add `ANTHROPIC_API_KEY`, `SUPABASE_URL`, and `SUPABASE_KEY` under Settings → Secrets in your Streamlit Cloud app.

---

## Project Structure

```
competitive-monitor/
├── app.py              # Streamlit dashboard (all five tabs)
├── scanner.py          # Scan orchestration — website → reviews → news → scoring
├── analyzer.py         # Claude API calls — all AI analysis and synthesis
├── database.py         # Supabase persistence layer
├── scraper.py          # Website scraper (requests + BeautifulSoup)
├── play_reviews.py     # Google Play Store review fetcher
├── news_client.py      # Google News RSS client
├── seed_data.py        # Historical event seed data (2022–2025)
├── config.py           # Competitor URLs, app IDs, weights, model config
├── schema.sql          # Supabase table definitions (run once in SQL Editor)
├── .env.example        # Credentials template
└── requirements.txt
```

---

## Author

**Ananya Chenat**
Master of Business Analytics, University of British Columbia
Marketing Technology Intern, Moneris

[LinkedIn](#) · [GitHub](#)
