"""Streamlit dashboard for the Moneris Competitive Intelligence Monitor."""

import email.utils
import html as _html
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import altair as alt
import pandas as pd
import streamlit as st

import database
import seed_data
from config import COMPARISON_DIMENSIONS, COMPETITORS, TARGET_COMPANY
from scanner import run_scan

st.set_page_config(
    page_title="Moneris Competitive Intel",
    page_icon="📊",
    layout="wide",
)

database.init_db()
seed_data.seed_if_empty()
seed_data.seed_website_changes_if_empty()
database.fix_error_threat_scores()

COMPETITOR_NAMES = list(COMPETITORS.keys())

COMPETITOR_COLORS = {
    "Stripe":           "#635BFF",  # Stripe purple
    "Square":           "#00B388",  # green
    "PayPal":           "#003087",  # PayPal navy
    "Shopify Payments": "#96BF48",  # Shopify green
    "Helcim":           "#E8335D",  # red/pink
    "Nuvei":            "#FF6B35",  # orange
    "Global Payments":  "#00A4E4",  # light blue
    "Clover":           "#1DA462",  # Clover green
}

# Ordered lists for Altair (preserves COMPETITOR_NAMES order)
_COLOR_DOMAIN = COMPETITOR_NAMES
_COLOR_RANGE  = [COMPETITOR_COLORS.get(c, "#94A3B8") for c in COMPETITOR_NAMES]

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
/* ── Base ─────────────────────────────────────────────── */
.stApp { background-color: #0B0F1A; }
.main .block-container { max-width: 1440px; padding-top: 1.1rem; padding-bottom: 2rem; }
[data-testid="stSidebar"] { background-color: #0F1623 !important; border-right: 1px solid #1E293B; }
hr { border-color: #1E293B !important; }

/* ── App header ────────────────────────────────────────── */
.app-title {
    font-size: 1.9rem; font-weight: 800; color: #F1F5F9;
    letter-spacing: -.025em; line-height: 1.2; margin-bottom: 2px;
}
.app-tagline { font-size: .85rem; color: #475569; margin-bottom: 0; }

/* ── KPI strip ─────────────────────────────────────────── */
.kpi-strip { display: flex; gap: 10px; flex-wrap: wrap; margin: 16px 0 20px; }
.kpi-card {
    flex: 1; min-width: 130px; background: #131A2E;
    border: 1px solid #1E293B; border-radius: 12px;
    padding: 14px 16px; text-align: center;
}
.kpi-name {
    font-size: .68rem; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #475569; margin-bottom: 6px;
}
.kpi-score { font-size: 1.85rem; font-weight: 800; line-height: 1; }
.kpi-delta { font-size: .72rem; font-weight: 600; margin-top: 5px; }
.sc-red   { color: #F87171; }
.sc-amber { color: #FBBF24; }
.sc-green { color: #34D399; }
.sc-grey  { color: #94A3B8; }
.dl-up  { color: #F87171; }
.dl-dn  { color: #34D399; }
.dl-eq  { color: #374151; }

/* ── Tabs ──────────────────────────────────────────────── */
[data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #1E293B !important;
    gap: 2px !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    color: #64748B !important;
    font-size: .875rem !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
    border-radius: 8px 8px 0 0 !important;
    transition: color .15s, background .15s !important;
}
[data-baseweb="tab"]:hover {
    color: #CBD5E1 !important;
    background: #131A2E !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #00D4AA !important;
    font-weight: 700 !important;
    border-bottom: 2px solid #00D4AA !important;
}
[data-baseweb="tab-highlight"] { display: none !important; }

/* ── Pill badges ───────────────────────────────────────── */
.pill {
    display: inline-block; padding: 2px 10px;
    border-radius: 99px; font-size: .74rem; font-weight: 700; white-space: nowrap;
}
.p-red    { background: rgba(239,68,68,.15);   color: #F87171; }
.p-amber  { background: rgba(251,191,36,.15);  color: #FBBF24; }
.p-green  { background: rgba(52,211,153,.15);  color: #34D399; }
.p-teal   { background: rgba(0,212,170,.15);   color: #00D4AA; }
.p-blue   { background: rgba(99,102,241,.15);  color: #A5B4FC; }
.p-purple { background: rgba(139,92,246,.15);  color: #C4B5FD; }
.p-grey   { background: rgba(148,163,184,.1);  color: #94A3B8; }

/* ── Comp badge ────────────────────────────────────────── */
.comp-badge {
    display: inline-block; padding: 2px 8px; border-radius: 5px;
    background: rgba(99,102,241,.15); color: #A5B4FC;
    font-size: .72rem; font-weight: 700;
}

/* ── Website changes table ─────────────────────────────── */
.wct { width: 100%; border-collapse: collapse; font-size: .86rem; }
.wct th {
    padding: 9px 12px; background: #0F172A; color: #475569;
    font-size: .68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; border-bottom: 1px solid #1E293B; text-align: left;
    white-space: normal; word-break: normal; overflow-wrap: anywhere;
}
.wct td {
    padding: 11px 12px; border-bottom: 1px solid #111827;
    vertical-align: top; color: #CBD5E1; word-break: break-word;
    line-height: 1.5;
}
.wct tr:hover td { background: rgba(255,255,255,.018); }
.wct tr:last-child td { border-bottom: none; }
.wct a { color: #818CF8; text-decoration: none; }
.wct a:hover { text-decoration: underline; }
.imp {
    display: inline-block; padding: 2px 9px;
    border-radius: 99px; font-size: .74rem; font-weight: 700;
}
.imp-hi  { background: rgba(239,68,68,.15);  color: #F87171; }
.imp-mid { background: rgba(251,191,36,.15); color: #FBBF24; }
.imp-lo  { background: rgba(52,211,153,.15); color: #34D399; }

/* ── Review cards ──────────────────────────────────────── */
.rv-card {
    background: #131A2E; border: 1px solid #1E293B; border-radius: 14px;
    padding: 20px 24px; margin-bottom: 14px;
}
.rv-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.rv-name { font-size: 1.1rem; font-weight: 700; color: #F1F5F9; }
.rv-sev-wrap { text-align: right; }
.rv-sev-num { font-size: 2.1rem; font-weight: 800; line-height: 1; }
.rv-sev-lbl { font-size: .65rem; color: #475569; text-transform: uppercase; letter-spacing: .08em; }
.rv-themes { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; }
.rv-section-label {
    font-size: .66rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .09em; margin-bottom: 7px;
}
.rv-label-red   { color: #F87171; }
.rv-label-green { color: #34D399; }
.rv-item { font-size: .84rem; color: #CBD5E1; padding: 3px 0; line-height: 1.4; }
.rv-item-r::before { content: "• "; color: #F87171; }
.rv-item-g::before { content: "• "; color: #34D399; }
.rv-metrics { display: flex; gap: 24px; margin-bottom: 14px; flex-wrap: wrap; }
.rv-metric-lbl { font-size: .67rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: #475569; margin-bottom: 2px; }
.rv-metric-val { font-size: .88rem; color: #94A3B8; }
.rv-opp {
    background: rgba(0,212,170,.07); border: 1px solid rgba(0,212,170,.22);
    border-radius: 8px; padding: 10px 14px; margin-top: 12px;
}
.rv-opp-title { font-size: .65rem; font-weight: 800; text-transform: uppercase; letter-spacing: .09em; color: #00D4AA; margin-bottom: 5px; }
.rv-opp-text { font-size: .86rem; color: #5EEAD4; line-height: 1.5; }
.rv-footer { font-size: .7rem; color: #374151; margin-top: 10px; }

/* ── News cards ─────────────────────────────────────────── */
.nc {
    background: #131A2E; border: 1px solid #1E293B; border-radius: 10px;
    padding: 14px 18px; margin-bottom: 10px;
}
.nc-hl { margin-bottom: 7px; }
.nc-hl a { font-size: .93rem; font-weight: 600; color: #E2E8F0; text-decoration: none; line-height: 1.4; }
.nc-hl a:hover { color: #00D4AA; }
.nc-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 5px; }
.nc-src { font-size: .72rem; color: #475569; }
.nc-sum { font-size: .82rem; color: #64748B; line-height: 1.5; margin-top: 4px; }
.rel-wrap { display: flex; align-items: center; gap: 8px; margin-top: 9px; }
.rel-label { font-size: .64rem; font-weight: 700; color: #374151; text-transform: uppercase; letter-spacing: .08em; white-space: nowrap; }
.rel-bg { flex: 1; height: 4px; background: #1E293B; border-radius: 99px; overflow: hidden; }
.rel-fill { height: 100%; border-radius: 99px; }
.rel-num { font-size: .72rem; font-weight: 700; color: #64748B; min-width: 30px; text-align: right; }

/* ── Comparison table ───────────────────────────────────── */
.cmpt { width: 100%; border-collapse: collapse; font-size: .875rem; }
.cmpt th {
    padding: 11px 10px; background: #0F172A; color: #475569;
    font-size: .68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .08em; border: 1px solid #1E293B; text-align: center;
}
.cmpt th:first-child { text-align: left; padding-left: 16px; }
.cmpt td { padding: 11px 10px; border: 1px solid #131A2E; text-align: center; }
.cmpt td:first-child { text-align: left; font-weight: 600; color: #CBD5E1; padding-left: 16px; }
.cmp-g { background: rgba(16,185,129,.1); color: #34D399; font-size: 1.05rem; font-weight: 800; }
.cmp-y { background: rgba(245,158,11,.1);  color: #FBBF24; font-size: 1.05rem; font-weight: 800; }
.cmp-r { background: rgba(239,68,68,.1);   color: #F87171; font-size: 1.05rem; font-weight: 800; }
.cmp-e { color: #374151; }

/* ── Alert cards ─────────────────────────────────────────── */
.ac { border-radius: 10px; padding: 16px 18px; }
.ac-threat { background: rgba(239,68,68,.06);   border: 1px solid rgba(239,68,68,.22); }
.ac-adv    { background: rgba(16,185,129,.06);  border: 1px solid rgba(16,185,129,.22); }
.ac-title { font-size: .68rem; font-weight: 800; text-transform: uppercase; letter-spacing: .09em; margin-bottom: 10px; }
.ac-threat .ac-title { color: #F87171; }
.ac-adv    .ac-title { color: #34D399; }
.ac-item {
    font-size: .88rem; color: #CBD5E1; padding: 5px 0;
    border-bottom: 1px solid rgba(255,255,255,.03); line-height: 1.45;
}
.ac-item:last-child { border-bottom: none; padding-bottom: 0; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _e(s) -> str:
    return _html.escape(str(s or ""))


def score_cls(score) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "sc-grey"
    if s >= 7:
        return "sc-red"
    if s >= 4:
        return "sc-amber"
    return "sc-green"


def impact_cls(score) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "imp-mid"
    if s >= 7:
        return "imp-hi"
    if s >= 4:
        return "imp-mid"
    return "imp-lo"


def sentiment_pill(sentiment: str) -> str:
    cls = {"negative": "p-red", "neutral": "p-grey", "positive": "p-green"}.get(sentiment, "p-grey")
    return f'<span class="pill {cls}">{_e(sentiment.title())}</span>'


def sev_cls(score) -> str:
    # High severity = unhappy competitor customers = Moneris opportunity = green
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "sc-grey"
    if s >= 7:
        return "sc-green"
    if s >= 4:
        return "sc-amber"
    return "sc-red"


def rel_color(score) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "#475569"
    if s >= 7:
        return "#F87171"
    if s >= 4:
        return "#FBBF24"
    return "#34D399"


def change_type_pill(ct: str) -> str:
    cls = {"pricing": "p-red", "feature": "p-teal", "policy": "p-amber", "UX": "p-blue"}.get(ct, "p-grey")
    return f'<span class="pill {cls}">{_e(ct)}</span>'


def _parse_news_date(date_str: str):
    """Parse a news published_at string (RFC 2822 or ISO) to an aware datetime, or None."""
    if not date_str:
        return None
    try:
        return email.utils.parsedate_to_datetime(date_str)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S+00:00",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str[:len(fmt)], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _format_news_date(date_str: str) -> str:
    """Return a human-friendly date string like 'May 23, 2024'."""
    dt = _parse_news_date(date_str)
    if dt:
        return dt.strftime("%b %d, %Y")
    return date_str[:10] if date_str else ""


def _parse_detected_at(s: str):
    """Parse a detected_at ISO timestamp string into an aware datetime, or epoch on failure."""
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def _deduplicate_changes(changes: list[dict]) -> list[dict]:
    """Remove near-duplicate changes (same competitor + day, description similarity > 65%)."""
    if not changes:
        return changes
    kept: list[dict] = []
    for change in changes:
        date_only = (change["detected_at"] or "").split("T")[0]
        competitor = change["competitor"]
        dup_idx = None
        for i, k in enumerate(kept):
            if k["competitor"] != competitor:
                continue
            if (k["detected_at"] or "").split("T")[0] != date_only:
                continue
            ratio = SequenceMatcher(None, change["description"], k["description"]).ratio()
            if ratio > 0.65:
                dup_idx = i
                break
        if dup_idx is not None:
            if change["customer_impact_score"] > kept[dup_idx]["customer_impact_score"]:
                kept[dup_idx] = change
        else:
            kept.append(change)
    return kept


# ---------------------------------------------------------------------------
# PDF export helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple:
    """Parse a #RRGGBB hex string into an (r, g, b) int tuple."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _safe_str(s) -> str:
    """Encode a string to Latin-1 for fpdf2 built-in fonts, replacing unknowns."""
    return str(s or "").encode("latin-1", errors="replace").decode("latin-1")


def _generate_pdf_report() -> bytes:
    """Generate the Moneris weekly brief as a PDF and return raw bytes."""
    from fpdf import FPDF  # lazy import so missing package doesn't break the app

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    now = datetime.now()

    # ── Dark header banner ──────────────────────────────────────────────────
    pdf.set_fill_color(11, 15, 26)
    pdf.rect(0, 0, 210, 36, "F")
    pdf.set_xy(15, 8)
    pdf.set_text_color(0, 212, 170)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(180, 10, "Moneris Competitive Intelligence Brief", align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(15, 22)
    pdf.set_text_color(148, 163, 184)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(180, 6,
             _safe_str(f"Weekly Brief  |  Exported: {now.strftime('%B %d, %Y at %H:%M')}  |  Powered by Claude AI"),
             align="C")
    pdf.set_y(42)

    # Last scan line
    last_scan = database.get_last_scan()
    pdf.set_text_color(100, 116, 139)
    pdf.set_font("Helvetica", "I", 8)
    if last_scan:
        pdf.set_x(15)
        pdf.cell(0, 5,
                 _safe_str(f"Last Scan: {last_scan['started_at']}  |  Status: {last_scan['status']}"))
    pdf.ln(7)

    def _section_header(title: str):
        y = pdf.get_y()
        pdf.set_fill_color(19, 26, 46)
        pdf.rect(15, y, 180, 7, "F")
        pdf.set_xy(18, y + 1)
        pdf.set_text_color(0, 212, 170)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, title.upper())
        pdf.set_y(y + 9)

    def _divider():
        pdf.set_draw_color(30, 41, 59)
        pdf.set_line_width(0.2)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(1.5)

    # ── Threat Scores ───────────────────────────────────────────────────────
    _section_header("Competitor Threat Scores")

    # Column widths: Competitor | Score | Trend | Attribution
    cw = [52, 25, 22, 81]
    latest_scores = database.get_latest_threat_scores()

    # Table header row
    pdf.set_text_color(71, 85, 105)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_fill_color(15, 23, 42)
    x0 = 15
    for i, (lbl, w) in enumerate(zip(["Competitor", "Score / 10", "Trend", "Attribution"], cw)):
        pdf.set_xy(x0 + sum(cw[:i]), pdf.get_y())
        pdf.cell(w, 5, lbl, fill=True)
    pdf.ln(5)
    _divider()

    for competitor in COMPETITOR_NAMES:
        row = latest_scores.get(competitor)
        if not row:
            continue
        score = float(row["threat_score"])
        prev = database.get_previous_threat_score(competitor)
        if prev:
            delta = score - float(prev["threat_score"])
            trend = (f"+{delta:.1f}" if delta > 0.05
                     else (f"{delta:.1f}" if delta < -0.05 else "stable"))
        else:
            trend = "first scan"

        r, g, b = _hex_to_rgb(COMPETITOR_COLORS.get(competitor, "#94A3B8"))
        reason_short = _safe_str((row.get("reason") or "")[:90])
        y = pdf.get_y()

        # Name in brand color
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(x0, y)
        pdf.cell(cw[0], 5.5, _safe_str(competitor))

        # Score in tier color
        if score >= 7:
            pdf.set_text_color(248, 113, 113)
        elif score >= 4:
            pdf.set_text_color(251, 191, 36)
        else:
            pdf.set_text_color(52, 211, 153)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(x0 + cw[0], y)
        pdf.cell(cw[1], 5.5, f"{score:.1f}", align="C")

        # Trend
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(x0 + cw[0] + cw[1], y)
        pdf.cell(cw[2], 5.5, trend, align="C")

        # Attribution (multi-cell advances Y)
        pdf.set_text_color(71, 85, 105)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_xy(x0 + cw[0] + cw[1] + cw[2], y)
        pdf.multi_cell(cw[3], 2.8, reason_short)

        pdf.set_y(max(pdf.get_y(), y + 5.5) + 0.5)
        _divider()

    pdf.ln(3)

    # ── Website Changes (top 5) ─────────────────────────────────────────────
    _section_header("Website Changes — Top 5 by Impact")

    changes = database.get_website_changes(limit=500)
    changes = [c for c in changes if c.get("customer_impact_score", 0) >= 2]
    changes = sorted(changes, key=lambda c: c.get("customer_impact_score", 0), reverse=True)[:5]

    for ch in changes:
        r, g, b = _hex_to_rgb(COMPETITOR_COLORS.get(ch["competitor"], "#94A3B8"))
        y = pdf.get_y()
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(15, y)
        pdf.cell(50, 5, _safe_str(ch["competitor"]))
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(35, 5, _safe_str((ch["detected_at"] or "")[:10]))
        sc_v = float(ch.get("customer_impact_score", 0))
        if sc_v >= 7:
            pdf.set_text_color(248, 113, 113)
        elif sc_v >= 4:
            pdf.set_text_color(251, 191, 36)
        else:
            pdf.set_text_color(52, 211, 153)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(30, 5, f"Impact: {sc_v:.0f}/10")
        pdf.ln(5)
        pdf.set_text_color(50, 60, 80)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_x(15)
        pdf.multi_cell(180, 3.8, _safe_str((ch["description"] or "")[:220]))
        pdf.ln(1.5)
        _divider()

    pdf.ln(2)

    # ── Customer Reviews ────────────────────────────────────────────────────
    _section_header("Customer Reviews — Top Complaints by Competitor")

    review_data = database.get_latest_review_sentiment()
    for competitor in COMPETITOR_NAMES:
        rec = review_data.get(competitor)
        if not rec:
            continue
        r, g, b = _hex_to_rgb(COMPETITOR_COLORS.get(competitor, "#94A3B8"))
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_x(15)
        pdf.cell(58, 5, _safe_str(competitor))
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Helvetica", "", 7)
        sev = float(rec.get("severity_score") or 0)
        pdf.cell(0, 5,
                 _safe_str(f"Sentiment: {rec.get('sentiment', '-')}  |  Severity: {sev:.1f}/10"))
        pdf.ln(5)
        for complaint in (rec.get("top_complaints") or [])[:2]:
            pdf.set_text_color(71, 85, 105)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_x(20)
            pdf.multi_cell(175, 3.5, _safe_str(f"- {complaint}"))
        opp = rec.get("moneris_opportunity") or ""
        if opp:
            pdf.set_text_color(0, 164, 132)
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_x(20)
            pdf.multi_cell(175, 3.5, _safe_str(f"Opp: {opp[:130]}"))
        pdf.ln(1.5)

    pdf.ln(2)

    # ── Latest News (top 5) ─────────────────────────────────────────────────
    _section_header("Latest News Highlights — Top 5 by Relevance")

    articles = database.get_news_articles(limit=500)
    articles = sorted(articles, key=lambda a: a.get("relevance_to_moneris", 0), reverse=True)[:5]

    for a in articles:
        rel = float(a.get("relevance_to_moneris") or 0)
        r, g, b = _hex_to_rgb(COMPETITOR_COLORS.get(a.get("competitor", ""), "#94A3B8"))
        y = pdf.get_y()
        pdf.set_text_color(r, g, b)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(15, y)
        pdf.cell(50, 5, _safe_str(a.get("competitor", "")))
        if rel >= 7:
            pdf.set_text_color(248, 113, 113)
        elif rel >= 4:
            pdf.set_text_color(251, 191, 36)
        else:
            pdf.set_text_color(52, 211, 153)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(35, 5, f"Relevance: {rel:.1f}/10")
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(0, 5, _safe_str((a.get("published_at") or "")[:10]))
        pdf.ln(5)
        pdf.set_text_color(50, 60, 80)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_x(15)
        pdf.multi_cell(180, 3.8, _safe_str((a.get("headline") or "")[:110]))
        if a.get("summary"):
            pdf.set_text_color(100, 116, 139)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_x(15)
            pdf.multi_cell(180, 3.5, _safe_str((a.get("summary") or "")[:160]))
        pdf.ln(1.5)
        _divider()

    pdf.ln(2)

    # ── Comparison Table ────────────────────────────────────────────────────
    _section_header("Moneris vs Competitors")

    card = database.get_latest_comparison_card()
    if card:
        comparison = card["comparison"]
        RATING_ICONS = {"green": "(+)", "yellow": "(~)", "red": "(-)"}
        RATING_COLORS = {
            "green":  (52, 211, 153),
            "yellow": (251, 191, 36),
            "red":    (248, 113, 113),
        }

        dim_w = 40
        n = len(COMPETITOR_NAMES)
        col_w = (180 - dim_w) / n

        # Header row
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(71, 85, 105)
        pdf.set_font("Helvetica", "B", 5.5)
        pdf.set_x(15)
        pdf.cell(dim_w, 5, "Dimension", fill=True)
        for c in COMPETITOR_NAMES:
            pdf.cell(col_w, 5, _safe_str(c[:9]), align="C", fill=True)
        pdf.ln(5)
        _divider()

        for dimension in COMPARISON_DIMENSIONS:
            pdf.set_text_color(100, 116, 139)
            pdf.set_font("Helvetica", "", 6.5)
            pdf.set_x(15)
            pdf.cell(dim_w, 4.5, _safe_str(dimension[:26]))
            for competitor in COMPETITOR_NAMES:
                cell = comparison.get(competitor, {}).get(dimension)
                if cell:
                    rating = cell.get("rating", "")
                    icon = RATING_ICONS.get(rating, "?")
                    rc = RATING_COLORS.get(rating, (100, 116, 139))
                    pdf.set_text_color(*rc)
                    pdf.set_font("Helvetica", "B", 6.5)
                    pdf.cell(col_w, 4.5, icon, align="C")
                    pdf.set_font("Helvetica", "", 6.5)
                    pdf.set_text_color(100, 116, 139)
                else:
                    pdf.cell(col_w, 4.5, "--", align="C")
            pdf.ln(4.5)

        pdf.set_font("Helvetica", "I", 6.5)
        pdf.set_text_color(71, 85, 105)
        pdf.set_x(15)
        pdf.ln(2)
        pdf.cell(0, 4,
                 "(+) = Moneris advantage  |  (~) = Comparable  |  (-) = Competitor advantage")
        pdf.ln(6)

        # ── Threats & Advantages ────────────────────────────────────────────
        _section_header("Top Threats & Moneris Advantages")
        pdf.ln(2)

        pdf.set_x(15)
        pdf.set_text_color(248, 113, 113)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, "Top Threats to Moneris")
        pdf.ln(5)
        for threat in card.get("top_threats", [])[:3]:
            pdf.set_text_color(71, 85, 105)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_x(18)
            pdf.multi_cell(177, 3.8, _safe_str(f"- {threat}"))
        pdf.ln(3)

        pdf.set_x(15)
        pdf.set_text_color(52, 211, 153)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, "Moneris Advantages to Leverage")
        pdf.ln(5)
        for adv in card.get("top_advantages", [])[:3]:
            pdf.set_text_color(71, 85, 105)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_x(18)
            pdf.multi_cell(177, 3.8, _safe_str(f"- {adv}"))

    # ── Footer ───────────────────────────────────────────────────────────────
    pdf.set_y(-18)
    pdf.set_draw_color(30, 41, 59)
    pdf.set_line_width(0.3)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)
    pdf.set_text_color(71, 85, 105)
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 5,
             _safe_str(f"Moneris Competitive Intelligence  |  Confidential  |  {now.strftime('%Y-%m-%d')}"),
             align="C")

    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# App header
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="app-title">📊 Moneris <span style="color:#00D4AA">Competitive</span> Intel</div>'
    '<div class="app-tagline">Real-time signals across 8 payment competitors &nbsp;·&nbsp; Powered by Claude AI</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPI strip — threat score per competitor
# ---------------------------------------------------------------------------

latest_scores = database.get_latest_threat_scores()
cards_html = ['<div class="kpi-strip">']
for competitor in COMPETITOR_NAMES:
    row = latest_scores.get(competitor)
    if row:
        score = row["threat_score"]
        sc = score_cls(score)
        prev = database.get_previous_threat_score(competitor)
        if prev:
            d = score - prev["threat_score"]
            if d > 0.05:
                delta_html = f'<div class="kpi-delta dl-up">&#9650; +{d:.1f} vs last scan</div>'
            elif d < -0.05:
                delta_html = f'<div class="kpi-delta dl-dn">&#9660; {d:.1f} vs last scan</div>'
            else:
                delta_html = '<div class="kpi-delta dl-eq">&#8212; stable vs last scan</div>'
        else:
            delta_html = '<div class="kpi-delta dl-eq">First scan</div>'
        c_color = COMPETITOR_COLORS.get(competitor, "#475569")
        cards_html.append(
            f'<div class="kpi-card" style="border-left:3px solid {c_color}">'
            f'<div class="kpi-name" style="color:{c_color}">{_e(competitor)}</div>'
            f'<div style="font-size:.6rem;color:#374151;text-transform:uppercase;letter-spacing:.07em;margin-bottom:3px">Threat Score</div>'
            f'<div class="kpi-score {sc}">{score:.1f}</div>'
            f'{delta_html}'
            f'</div>'
        )
    else:
        c_color = COMPETITOR_COLORS.get(competitor, "#475569")
        cards_html.append(
            f'<div class="kpi-card" style="border-left:3px solid {c_color}">'
            f'<div class="kpi-name" style="color:{c_color}">{_e(competitor)}</div>'
            f'<div style="font-size:.6rem;color:#374151;text-transform:uppercase;letter-spacing:.07em;margin-bottom:3px">Threat Score</div>'
            f'<div class="kpi-score sc-grey">&#8212;</div>'
            f'<div class="kpi-delta dl-eq">No data</div>'
            f'</div>'
        )
cards_html.append('</div>')
cards_html.append(
    '<div style="font-size:.72rem;color:#374151;margin-top:-8px;margin-bottom:4px">'
    'Threat scores calculated from website changes, app reviews, and news signals &nbsp;&#183;&nbsp; '
    'Scale: 1&#8211;10 &nbsp;&#183;&nbsp; Higher = greater competitive threat to Moneris'
    '</div>'
)
st.markdown("".join(cards_html), unsafe_allow_html=True)

st.divider()


# ---------------------------------------------------------------------------
# Sidebar — Run Scan
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🔍 Run Scan")
    st.caption(
        "Scans all 8 competitors across website pricing/product pages, "
        "Google Play Store app reviews, and Google News, then runs AI analysis "
        "and updates the dashboard."
    )

    run_clicked = st.button("🚀 Run Full Scan", type="primary", use_container_width=True)

    last_scan = database.get_last_scan()
    if last_scan:
        st.caption(f"Last scan: {last_scan['started_at']}")
        st.caption(f"Status: {last_scan['status']}")

    if run_clicked:
        log_placeholder = st.empty()
        log_lines: list[str] = []

        def progress_callback(message: str) -> None:
            log_lines.append(message)
            log_placeholder.code("\n".join(log_lines[-25:]))

        with st.spinner("Running full scan..."):
            try:
                result = run_scan(progress_callback=progress_callback)
            except RuntimeError as exc:
                st.error(str(exc))
                result = None

        if result is not None:
            st.success(
                f"Scanned {result['competitors_scanned']} competitors. "
                f"{result['website_changes_found']} website change(s), "
                f"{result['news_articles_found']} news article(s)."
            )
            if result["errors"]:
                with st.expander(f"{len(result['errors'])} warning(s)"):
                    for err in result["errors"]:
                        st.markdown(f"- {err}")
            st.info("Refresh to see updated results.")

    st.divider()
    st.markdown("### 📄 Export Report")
    st.caption("Generate a PDF summary of all current competitive intelligence.")

    if "pdf_bytes" not in st.session_state:
        st.session_state.pdf_bytes = None

    if st.button("📄 Export Weekly Brief", use_container_width=True):
        with st.spinner("Generating PDF..."):
            try:
                st.session_state.pdf_bytes = _generate_pdf_report()
            except Exception as exc:
                st.error(f"PDF generation failed: {exc}")
                st.session_state.pdf_bytes = None

    if st.session_state.pdf_bytes:
        st.download_button(
            label="⬇ Download PDF",
            data=st.session_state.pdf_bytes,
            file_name=f"moneris_weekly_brief_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌐 Website Changes",
    "⭐ Customer Reviews",
    "📰 Latest News",
    "⚖️ Moneris vs Competitors",
    "📈 Trends",
])


# ---------------------------------------------------------------------------
# Tab 1 — Website Changes
# ---------------------------------------------------------------------------

with tab1:
    st.markdown(
        "**Website Changes** &nbsp;"
        "<span style='color:#475569;font-size:.85rem'>Detected changes to competitor pricing and product pages</span>",
        unsafe_allow_html=True,
    )
    st.write("")

    fc1, fc2 = st.columns(2)
    with fc1:
        wc_competitor = st.selectbox("Competitor", ["All"] + COMPETITOR_NAMES, key="wc_c")
    with fc2:
        wc_change_type = st.selectbox("Change type", ["All", "pricing", "feature", "policy", "UX"], key="wc_ct")
    st.caption(f"Showing changes from the last 90 days · older data retained in database for trend analysis")

    changes = database.get_website_changes(limit=500, competitor=wc_competitor, change_type=wc_change_type)
    # Filter out low-impact (score < 2) entries already in the DB from earlier scans
    changes = [c for c in changes if c.get("customer_impact_score", 0) >= 2]
    # Only show changes from the last 90 days
    _cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    changes = [c for c in changes if _parse_detected_at(c.get("detected_at", "")) >= _cutoff]
    # Remove near-duplicates: same competitor + day with similar descriptions
    changes = _deduplicate_changes(changes)

    if not changes:
        st.info("No website changes recorded yet. Run a scan from the sidebar to get started.")
    else:
        headers = ["Date", "Competitor", "Link", "Type", "What Changed", "Impact", "Revenue Sensitivity", "Segment"]
        col_widths = ["8%", "10%", "5%", "7%", "38%", "9%", "11%", "8%"]

        colgroup = "".join(f'<col style="width:{w}">' for w in col_widths)
        ths = "".join(f'<th>{_e(h)}</th>' for h in headers)

        rows_html = []
        for ch in changes:
            date_only = (ch["detected_at"] or "").split("T")[0]
            rows_html.append(
                f'<tr>'
                f'<td style="color:#64748B;font-size:.8rem">{_e(date_only)}</td>'
                f'<td><span class="comp-badge">{_e(ch["competitor"])}</span></td>'
                f'<td><a href="{_e(ch["url"])}" target="_blank">&#8599;</a></td>'
                f'<td>{change_type_pill(ch["change_type"])}</td>'
                f'<td style="color:#E2E8F0">{_e(ch["description"])}</td>'
                f'<td style="text-align:center"><span class="imp {impact_cls(ch["customer_impact_score"])}">'
                f'{ch["customer_impact_score"]}/10</span></td>'
                f'<td style="color:#94A3B8;font-size:.82rem">{_e(ch["revenue_sensitivity"])}</td>'
                f'<td style="color:#94A3B8;font-size:.82rem">{_e(ch["segment_affected"])}</td>'
                f'</tr>'
            )

        st.markdown(
            f'<table class="wct"><colgroup>{colgroup}</colgroup>'
            f'<tr>{ths}</tr>'
            + "".join(rows_html)
            + "</table>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab 2 — Customer Reviews (Google Play Store)
# ---------------------------------------------------------------------------

with tab2:
    st.markdown(
        "**Customer Reviews — Google Play Store** &nbsp;"
        "<span style='color:#475569;font-size:.85rem'>Claude-analyzed app review sentiment, themes, and Moneris opportunities</span>",
        unsafe_allow_html=True,
    )
    st.write("")

    review_data = database.get_latest_review_sentiment()

    if not review_data:
        st.info("No review data yet. Run a scan from the sidebar to get started.")
    else:
        cards = []
        for competitor in COMPETITOR_NAMES:
            rec = review_data.get(competitor)
            if not rec:
                cards.append(
                    f'<div class="rv-card">'
                    f'<div class="rv-header"><div class="rv-name">{_e(competitor)}</div></div>'
                    f'<div style="color:#475569;font-size:.85rem">No review data yet for this competitor.</div>'
                    f'</div>'
                )
                continue

            sev = rec["severity_score"]
            sc = sev_cls(sev)

            theme_pills = " ".join(
                f'<span class="pill p-grey">{_e(t)}</span>'
                for t in (rec["themes"] or [])
            )

            complaints_html = "".join(
                f'<div class="rv-item rv-item-r">{_e(c)}</div>'
                for c in (rec["top_complaints"] or [])
            ) or '<div style="color:#374151;font-size:.82rem">None found</div>'

            praise_html = "".join(
                f'<div class="rv-item rv-item-g">{_e(p)}</div>'
                for p in (rec["top_praise"] or [])
            ) or '<div style="color:#374151;font-size:.82rem">None found</div>'

            breakdown = rec.get("source_breakdown") or {}
            breakdown_str = ", ".join(f"{s}: {n}" for s, n in breakdown.items()) if breakdown else "—"

            themes_row = f'<div class="rv-themes">{theme_pills}</div>' if theme_pills else ""

            cards.append(
                f'<div class="rv-card">'
                # Header: name + sentiment badge left, severity score right
                f'<div class="rv-header">'
                f'<div><div class="rv-name">{_e(competitor)}</div>'
                f'<div style="margin-top:5px">{sentiment_pill(rec["sentiment"])}</div></div>'
                f'<div class="rv-sev-wrap">'
                f'<div class="rv-sev-num {sc}">{sev:.1f}</div>'
                f'<div class="rv-sev-lbl">/ 10 severity</div>'
                f'</div>'
                f'</div>'
                # Metrics
                f'<div class="rv-metrics">'
                f'<div><div class="rv-metric-lbl">Reviews analyzed</div>'
                f'<div class="rv-metric-val">{rec["review_count"]}</div></div>'
                f'<div><div class="rv-metric-lbl">Source</div>'
                f'<div class="rv-metric-val">{_e(breakdown_str)}</div></div>'
                f'</div>'
                # Themes
                + themes_row
                # Complaints / Praise two-column
                + f'<div style="display:flex;gap:20px">'
                f'<div style="flex:1"><div class="rv-section-label rv-label-red">Top complaints</div>'
                f'{complaints_html}</div>'
                f'<div style="flex:1"><div class="rv-section-label rv-label-green">Top praise</div>'
                f'{praise_html}</div>'
                f'</div>'
                # Opportunity box
                + f'<div class="rv-opp">'
                f'<div class="rv-opp-title">Moneris opportunity</div>'
                f'<div class="rv-opp-text">{_e(rec["moneris_opportunity"])}</div>'
                f'</div>'
                + f'<div class="rv-footer">Last updated: {_e(rec["scanned_at"])}</div>'
                f'</div>'
            )

        st.markdown("".join(cards), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab 3 — Latest News
# ---------------------------------------------------------------------------

with tab3:
    st.markdown(
        "**Latest News** &nbsp;"
        "<span style='color:#475569;font-size:.85rem'>Recent articles sorted by Moneris relevance</span>",
        unsafe_allow_html=True,
    )
    st.write("")

    nc1, nc2 = st.columns(2)
    with nc1:
        news_competitor = st.selectbox("Competitor", ["All"] + COMPETITOR_NAMES, key="news_c")
    with nc2:
        impact_types = ["All", "pricing_change", "product_launch", "policy_change", "funding", "partnership", "other"]
        news_impact_type = st.selectbox("Impact type", impact_types, key="news_it")

    articles = database.get_news_articles(limit=500, competitor=news_competitor, impact_type=news_impact_type)
    # Keep only articles from the last 90 days; include articles with unparseable dates
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=90)
    articles = [
        a for a in articles
        if (dt := _parse_news_date(a.get("published_at", ""))) is None or dt >= cutoff_dt
    ]

    if not articles:
        st.info("No news articles from the last 90 days. Run a scan to fetch the latest news.")
    else:
        impact_pill_cls = {
            "pricing_change": "p-red",
            "product_launch": "p-teal",
            "policy_change": "p-amber",
            "funding": "p-green",
            "partnership": "p-blue",
            "other": "p-grey",
        }
        sw_pill_cls = {"high": "p-teal", "medium": "p-amber", "low": "p-grey"}

        cards = []
        for a in articles:
            rel = a.get("relevance_to_moneris", 0)
            rc = rel_color(rel)
            pct = min(100, int(rel * 10))
            it_raw = a.get("impact_type") or "other"
            it_label = it_raw.replace("_", " ")
            it_cls = impact_pill_cls.get(it_raw, "p-grey")
            date_formatted = _format_news_date(a.get("published_at") or "")
            sw = a.get("source_weight") or ""
            sw_html = f'<span class="pill {sw_pill_cls.get(sw, "p-grey")}">{_e(sw)}</span>' if sw else ""
            url = _e(a.get("url") or "#")
            hl = _e(a.get("headline") or "")
            src = _e(a.get("source") or "")
            summary = _e(a.get("summary") or "")
            comp = _e(a.get("competitor") or "")

            date_html = (
                f'<span class="nc-src">Published {_e(date_formatted)}</span>'
                if date_formatted else ""
            )
            cards.append(
                f'<div class="nc">'
                f'<div class="nc-hl"><a href="{url}" target="_blank">{hl}</a></div>'
                f'<div class="nc-meta">'
                f'<span class="comp-badge">{comp}</span>'
                f'<span class="pill {it_cls}">{_e(it_label)}</span>'
                f'{sw_html}'
                + (f'<span class="nc-src">{src}</span>' if src else '')
                + date_html
                + f'</div>'
                + (f'<div class="nc-sum">{summary}</div>' if summary else '')
                + f'<div class="rel-wrap">'
                f'<span class="rel-label">Relevance</span>'
                f'<div class="rel-bg"><div class="rel-fill" style="width:{pct}%;background:{rc}"></div></div>'
                f'<span class="rel-num">{rel}/10</span>'
                f'</div>'
                f'</div>'
            )

        st.markdown("".join(cards), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab 4 — Moneris vs Competitors
# ---------------------------------------------------------------------------

with tab4:
    st.markdown(
        f'**{_e(TARGET_COMPANY)} vs Competitors** &nbsp;'
        '<span style="color:#475569;font-size:.85rem">AI-generated comparison across key dimensions, refreshed each scan</span>',
        unsafe_allow_html=True,
    )
    st.write("")

    card = database.get_latest_comparison_card()

    if not card:
        st.info("No comparison card yet. Run a scan from the sidebar to generate one.")
    else:
        comparison = card["comparison"]
        ICONS = {"green": "&#10003;", "yellow": "&asymp;", "red": "&#10007;"}
        CSS_CLS = {"green": "cmp-g", "yellow": "cmp-y", "red": "cmp-r"}

        ths = '<th style="min-width:160px">Dimension</th>' + "".join(
            f'<th>{_e(c)}</th>' for c in COMPETITOR_NAMES
        )
        rows_html = []
        for dimension in COMPARISON_DIMENSIONS:
            cells = ""
            for competitor in COMPETITOR_NAMES:
                cell = comparison.get(competitor, {}).get(dimension)
                if cell:
                    rating = cell.get("rating", "")
                    icon = ICONS.get(rating, "?")
                    cls = CSS_CLS.get(rating, "cmp-e")
                    note = _e(cell.get("note", ""))
                    cells += f'<td class="{cls}" title="{note}">{icon}</td>'
                else:
                    cells += '<td class="cmp-e">&#8212;</td>'
            rows_html.append(f'<tr><td>{_e(dimension)}</td>{cells}</tr>')

        st.markdown(
            f'<table class="cmpt"><tr>{ths}</tr>' + "".join(rows_html) + "</table>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Hover over a cell to see the reasoning. "
            "&#10003; Moneris advantage &nbsp;·&nbsp; &asymp; Comparable &nbsp;·&nbsp; &#10007; Competitor advantage"
        )

        st.write("")

        col_threat, col_adv = st.columns(2)

        with col_threat:
            threat_items = "".join(
                f'<div class="ac-item">{_e(t)}</div>' for t in card["top_threats"]
            )
            st.markdown(
                f'<div class="ac ac-threat">'
                f'<div class="ac-title">&#9650; Top threats to {_e(TARGET_COMPANY)} this week</div>'
                f'{threat_items}'
                f'</div>',
                unsafe_allow_html=True,
            )

        with col_adv:
            adv_items = "".join(
                f'<div class="ac-item">{_e(a)}</div>' for a in card["top_advantages"]
            )
            st.markdown(
                f'<div class="ac ac-adv">'
                f'<div class="ac-title">&#10003; {_e(TARGET_COMPANY)} advantages to leverage</div>'
                f'{adv_items}'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.caption(f"Generated: {card['generated_at']}")


# ---------------------------------------------------------------------------
# Tab 5 — Trends
# ---------------------------------------------------------------------------

with tab5:
    st.markdown(
        "**Threat Score Trends** &nbsp;"
        "<span style='color:#475569;font-size:.85rem'>Threat score over time per competitor with attribution</span>",
        unsafe_allow_html=True,
    )
    st.write("")

    history = database.get_threat_score_history()

    if not history:
        st.info("No threat score history yet. Run a scan from the sidebar to get started.")
    else:
        df = pd.DataFrame(history)
        df["scanned_at"] = pd.to_datetime(df["scanned_at"])

        chart = (
            alt.Chart(df)
            .mark_line(point=alt.OverlayMarkDef(size=60, filled=True))
            .encode(
                x=alt.X(
                    "scanned_at:T",
                    title="Date",
                    axis=alt.Axis(
                        labelColor="#64748B", titleColor="#64748B",
                        gridColor="#1E293B", domainColor="#1E293B",
                        tickCount="year",
                        format="%Y",
                    ),
                ),
                y=alt.Y(
                    "threat_score:Q",
                    title="Threat Score",
                    scale=alt.Scale(domain=[0, 10]),
                    axis=alt.Axis(
                        labelColor="#64748B", titleColor="#64748B",
                        gridColor="#1E293B", domainColor="#1E293B",
                    ),
                ),
                color=alt.Color(
                    "competitor:N",
                    title="Competitor",
                    scale=alt.Scale(domain=_COLOR_DOMAIN, range=_COLOR_RANGE),
                    legend=alt.Legend(labelColor="#CBD5E1", titleColor="#94A3B8"),
                ),
                tooltip=[
                    alt.Tooltip("competitor:N", title="Competitor"),
                    alt.Tooltip("scanned_at:T", title="Date", format="%Y-%m-%d"),
                    alt.Tooltip("threat_score:Q", title="Threat Score", format=".1f"),
                    alt.Tooltip("reason:N", title="Why"),
                ],
            )
            .properties(height=420)
            .configure_view(strokeOpacity=0, fill="#131A2E")
            .configure_legend(
                fillColor="#131A2E", strokeColor="#1E293B", padding=10,
                labelFontSize=12, titleFontSize=11,
            )
            .interactive()
        )

        st.altair_chart(chart, use_container_width=True)
        st.caption("Historical data seeded from real market events. New data points added with each weekly scan.")

        st.divider()
        st.markdown("**Latest Threat Scores**", unsafe_allow_html=True)
        st.write("")

        latest = database.get_latest_threat_scores()
        rows = []
        for competitor in COMPETITOR_NAMES:
            row = latest.get(competitor)
            if row:
                rows.append({
                    "Competitor": competitor,
                    "Threat Score": row["threat_score"],
                    "App Review": row["reddit_component"],
                    "News Momentum": row["news_component"],
                    "Feature Velocity": row["feature_velocity_component"],
                    "SMB Relevance": row["smb_relevance_component"],
                    "Why": row["reason"],
                    "Last Updated": row["scanned_at"],
                })
        if rows:
            # ts_headers: logical keys used for tooltip lookup and data access
            # ts_display: HTML shown in the <th>; explicit <br> prevents mid-word breaks
            ts_headers = ["Competitor", "Score", "App Reviews", "News Score", "Feature Velocity", "SMB Relevance", "Why It Changed", "Last Updated"]
            ts_display = ["Competitor", "Score", "App<br>Reviews", "News<br>Score", "Feature<br>Velocity", "SMB<br>Relevance", "Why It Changed", "Last Updated"]
            ts_tooltips = {
                "Feature Velocity": "Rate of product/pricing page changes detected",
            }
            ts_widths = ["9%", "6%", "8%", "6%", "9%", "7%", "48%", "7%"]
            colgroup = "".join(f'<col style="width:{w}">' for w in ts_widths)
            ths_html = "".join(
                f'<th title="{ts_tooltips[h]}" style="cursor:help;text-decoration:underline dotted #475569">{disp}</th>'
                if h in ts_tooltips else f'<th>{disp}</th>'
                for h, disp in zip(ts_headers, ts_display)
            )

            score_colors = {
                "hi":  ("rgba(239,68,68,.15)",   "#F87171"),
                "mid": ("rgba(251,191,36,.15)",  "#FBBF24"),
                "lo":  ("rgba(52,211,153,.15)",  "#34D399"),
            }

            ts_rows = []
            for r in rows:
                sc_float = float(r["Threat Score"])
                tier = "hi" if sc_float >= 7 else ("mid" if sc_float >= 4 else "lo")
                bg, fg = score_colors[tier]
                date_only = str(r["Last Updated"] or "")[:10]
                ts_rows.append(
                    f'<tr>'
                    f'<td><span class="comp-badge">{_e(r["Competitor"])}</span></td>'
                    f'<td style="text-align:center;background:{bg}">'
                    f'<strong style="color:{fg}">{sc_float:.1f}</strong></td>'
                    f'<td style="text-align:center;color:#94A3B8">{float(r["App Review"]):.1f}</td>'
                    f'<td style="text-align:center;color:#94A3B8">{float(r["News Momentum"]):.1f}</td>'
                    f'<td style="text-align:center;color:#94A3B8">{float(r["Feature Velocity"]):.1f}</td>'
                    f'<td style="text-align:center;color:#94A3B8">{float(r["SMB Relevance"]):.1f}</td>'
                    f'<td style="white-space:normal;word-break:break-word;line-height:1.5;color:#CBD5E1">{_e(r["Why"])}</td>'
                    f'<td style="color:#64748B;font-size:.78rem;white-space:nowrap">{_e(date_only)}</td>'
                    f'</tr>'
                )

            st.markdown(
                f'<table class="wct"><colgroup>{colgroup}</colgroup>'
                f'<tr>{ths_html}</tr>'
                + "".join(ts_rows)
                + "</table>",
                unsafe_allow_html=True,
            )

        with st.expander("Historical events (seed data)"):
            events = database.get_historical_events()
            if events:
                ev_headers = ["Date", "Competitor", "Event Type", "Description", "Source", "Impact"]
                ev_widths  = ["8%", "10%", "11%", "47%", "16%", "8%"]
                ev_colgroup = "".join(f'<col style="width:{w}">' for w in ev_widths)
                ev_ths = "".join(f'<th>{h}</th>' for h in ev_headers)

                ev_rows = []
                for ev in events:
                    ev_rows.append(
                        f'<tr>'
                        f'<td style="color:#64748B;font-size:.78rem;white-space:nowrap">{_e(ev["date"])}</td>'
                        f'<td><span class="comp-badge">{_e(ev["competitor"])}</span></td>'
                        f'<td><span class="pill p-grey">{_e(ev["event_type"])}</span></td>'
                        f'<td style="white-space:normal;word-break:break-word;line-height:1.5;color:#CBD5E1">'
                        f'{_e(ev["description"])}</td>'
                        f'<td style="color:#94A3B8;font-size:.82rem">{_e(ev["source"])}</td>'
                        f'<td style="text-align:center"><span class="imp {impact_cls(ev["impact_score"])}">'
                        f'{ev["impact_score"]}/10</span></td>'
                        f'</tr>'
                    )

                st.markdown(
                    f'<table class="wct"><colgroup>{ev_colgroup}</colgroup>'
                    f'<tr>{ev_ths}</tr>'
                    + "".join(ev_rows)
                    + "</table>",
                    unsafe_allow_html=True,
                )
