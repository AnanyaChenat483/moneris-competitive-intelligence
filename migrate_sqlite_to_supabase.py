"""One-time migration: copy all website_changes from local SQLite to Supabase,
then insert the historical seed data.

Run once from the project root with Supabase credentials in .env:
    python migrate_sqlite_to_supabase.py
"""

import sqlite3
import os
import sys

import database
from seed_data import WEBSITE_CHANGES_SEED

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "data", "monitor.db")


def migrate():
    # --- 1. Read all rows from SQLite ---
    print(f"Reading from SQLite: {SQLITE_PATH}")
    if not os.path.exists(SQLITE_PATH):
        print("ERROR: SQLite database not found at", SQLITE_PATH)
        sys.exit(1)

    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM website_changes ORDER BY id").fetchall()
    conn.close()
    print(f"Found {len(rows)} rows in SQLite website_changes\n")

    # --- 2. Insert SQLite rows into Supabase ---
    print("--- Migrating SQLite rows ---")
    sqlite_ok = 0
    for row in rows:
        r = dict(row)
        try:
            database.insert_website_change(
                competitor=r["competitor"],
                page_type=r["page_type"],
                url=r["url"],
                change_type=r["change_type"],
                description=r["description"],
                customer_impact_score=int(r["customer_impact_score"]),
                revenue_sensitivity=r["revenue_sensitivity"],
                segment_affected=r["segment_affected"],
                diff=r["diff"],
                detected_at=r["detected_at"],
            )
            print(
                f"  [OK] id={r['id']} {r['competitor']} / {r['page_type']} "
                f"| {r['change_type']} impact={r['customer_impact_score']} "
                f"| {r['detected_at']}"
            )
            sqlite_ok += 1
        except Exception as exc:
            print(f"  [FAIL] id={r['id']} {r['competitor']}: {exc}")

    print(f"\nSQLite migration: {sqlite_ok}/{len(rows)} rows inserted\n")

    # --- 3. Insert historical seed data ---
    print("--- Inserting historical seed data ---")
    seed_ok = 0
    for change in WEBSITE_CHANGES_SEED:
        try:
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
            print(
                f"  [OK] {change['detected_at'][:10]} {change['competitor']} / {change['page_type']} "
                f"| {change['change_type']} impact={change['customer_impact_score']}"
            )
            seed_ok += 1
        except Exception as exc:
            print(f"  [FAIL] {change['competitor']} {change['detected_at'][:10]}: {exc}")

    print(f"\nSeed data: {seed_ok}/{len(WEBSITE_CHANGES_SEED)} rows inserted")

    # --- 4. Verify total in Supabase ---
    print("\n--- Verifying Supabase ---")
    total = database.get_website_changes(limit=500)
    print(f"Total rows now in Supabase website_changes: {len(total)}")

    print("\nDone.")


if __name__ == "__main__":
    migrate()
