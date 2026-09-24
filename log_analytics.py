"""Interactive analytics logger — updates Airtable Posts with 14-day analytics."""

import os
import sys
from datetime import date

from dotenv import load_dotenv
from pyairtable import Api

load_dotenv()

BASE_ID = "app5LdHmUEycVYeh1"
TABLE_ID = "tbl8L67GarvyY05ZI"

STATUS_COLLECTED = "✅ Collected"

# Fields the user fills in, in prompt order
ANALYTICS_FIELDS = [
    ("Impressions",      "Impressions",      "number"),
    ("Clicks",           "Clicks",           "number"),
    ("Engagements",      "Engagements",      "number"),
    ("Reposts/Share",    "Reposts/Share",     "number"),
    ("Followers Gained", "Followers Gained",  "number"),
    ("Engagement Rate",  "Engagement Rate",   "percent"),  # enter as %, stored as decimal
]

DIVIDER = "─" * 56


def fetch_due_posts(api_key: str) -> list[dict]:
    api = Api(api_key)
    table = api.table(BASE_ID, TABLE_ID)

    formula = (
        "AND("
        '  {Analytics Status} != "✅ Collected",'
        '  NOT({Analytics Due Date} = ""),'
        "  IS_BEFORE({Analytics Due Date}, DATEADD(TODAY(), 1, 'days'))"
        ")"
    )

    records = table.all(
        fields=[
            "Name", "Date", "Platform",
            "Analytics Due Date", "Analytics Status",
            "Impressions", "Clicks", "Engagements",
            "Reposts/Share", "Followers Gained", "Engagement Rate",
        ],
        formula=formula,
        sort=["Analytics Due Date"],
    )

    posts = []
    for r in records:
        f = r["fields"]
        posts.append({
            "id": r["id"],
            "name": f.get("Name", "(untitled)"),
            "date": f.get("Date", "—"),
            "platform": f.get("Platform", "—"),
            "due_date": f.get("Analytics Due Date", "—"),
            "status": f.get("Analytics Status", ""),
            "existing": {
                "Impressions":      f.get("Impressions"),
                "Clicks":           f.get("Clicks"),
                "Engagements":      f.get("Engagements"),
                "Reposts/Share":    f.get("Reposts/Share"),
                "Followers Gained": f.get("Followers Gained"),
                "Engagement Rate":  f.get("Engagement Rate"),
            },
        })
    return posts


def prompt_number(label: str, existing) -> float | None:
    existing_str = f"  [current: {existing}]" if existing is not None else ""
    raw = input(f"  {label}{existing_str}: ").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        print(f"  ✗ Not a number — skipping {label}")
        return None


def log_post(post: dict, table) -> bool:
    """Prompt user for analytics, update Airtable. Returns True if updated."""
    print()
    print(DIVIDER)
    print(f"  {post['name']}")
    print(f"  {post['platform']}  ·  Posted {post['date']}  ·  Due {post['due_date']}")
    if post["status"]:
        print(f"  Status: {post['status']}")
    print(DIVIDER)
    print("  Enter values (blank = keep existing)  |  's' = skip this post")
    print()

    action = input("  [Enter] to log  or  's' to skip: ").strip().lower()
    if action == "s":
        return False

    updates: dict = {}

    for field_key, prompt_label, field_type in ANALYTICS_FIELDS:
        existing = post["existing"].get(field_key)

        if field_type == "percent":
            existing_str = f"  [current: {existing * 100:.2f}%]" if existing is not None else ""
            raw = input(f"  {prompt_label} (enter as %, e.g. 5.2){existing_str}: ").strip()
            if raw:
                try:
                    updates[field_key] = float(raw) / 100
                except ValueError:
                    print(f"  ✗ Not a number — skipping {prompt_label}")
        else:
            val = prompt_number(prompt_label, existing)
            if val is not None:
                updates[field_key] = val

    if not updates:
        confirm = input("\n  No values entered. Mark as Collected anyway? [y/N]: ").strip().lower()
        if confirm != "y":
            print("  → Skipped (no changes made)")
            return False

    updates["Analytics Status"] = STATUS_COLLECTED

    table.update(post["id"], updates)
    print(f"  ✓ Saved — marked as {STATUS_COLLECTED}")
    return True


def main() -> None:
    api_key = os.getenv("AIRTABLE_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("ERROR: Set AIRTABLE_API_KEY in your .env file.")
        sys.exit(1)

    print("Fetching posts due for analytics…")
    api = Api(api_key)
    table = api.table(BASE_ID, TABLE_ID)
    posts = fetch_due_posts(api_key)

    if not posts:
        print("No posts are currently due for analytics. You're all caught up!")
        sys.exit(0)

    total = len(posts)
    print(f"Found {total} post{'s' if total != 1 else ''} due for analytics.\n")

    logged = 0
    skipped = 0

    for i, post in enumerate(posts, 1):
        print(f"\nPost {i} of {total}:")
        updated = log_post(post, table)
        if updated:
            logged += 1
        else:
            skipped += 1

    print()
    print("═" * 56)
    print(f"  Done!  Logged: {logged}  ·  Skipped: {skipped}  ·  Total: {total}")
    print("═" * 56)
    print()


if __name__ == "__main__":
    main()
