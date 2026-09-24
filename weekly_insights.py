"""Weekly social media insights report from Airtable Posts table."""

import os
from collections import defaultdict
from datetime import datetime, timedelta

from dotenv import load_dotenv
from pyairtable import Api

load_dotenv()

BASE_ID = "app5LdHmUEycVYeh1"
TABLE_ID = "tbl8L67GarvyY05ZI"  # Posts


def fetch_posts_with_analytics(api_key: str) -> list[dict]:
    api = Api(api_key)
    table = api.table(BASE_ID, TABLE_ID)

    # Pull all posts where Impressions is not empty
    records = table.all(
        fields=[
            "Name",
            "Date",
            "Platform",
            "Impressions",
            "Engagements",
            "Clicks",
            "Engagement Rate",
            "CTR",
            "Month",
        ],
        formula="NOT({Impressions} = '')",
    )

    posts = []
    for r in records:
        f = r["fields"]
        posts.append(
            {
                "name": f.get("Name", "(untitled)"),
                "date": f.get("Date", ""),
                "platform": f.get("Platform", "Unknown"),
                "impressions": f.get("Impressions", 0),
                "engagements": f.get("Engagements", 0),
                "clicks": f.get("Clicks", 0),
                "engagement_rate": f.get("Engagement Rate"),  # stored as decimal (0.05 = 5%)
                "ctr": f.get("CTR"),
                "month": f.get("Month", ""),
            }
        )
    return posts


def top_5_by_engagement(posts: list[dict]) -> list[dict]:
    ranked = [p for p in posts if p["engagement_rate"] is not None]
    ranked.sort(key=lambda p: p["engagement_rate"], reverse=True)
    return ranked[:5]


def avg_engagement_by_platform(posts: list[dict]) -> dict[str, float]:
    platform_rates: dict[str, list[float]] = defaultdict(list)
    for p in posts:
        if p["engagement_rate"] is not None:
            platform_rates[p["platform"]].append(p["engagement_rate"])

    return {
        platform: sum(rates) / len(rates)
        for platform, rates in sorted(platform_rates.items())
    }


def pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.2f}%"


def divider(char: str = "─", width: int = 60) -> str:
    return char * width


def print_report(posts: list[dict]) -> None:
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).strftime("%B %d")
    week_end = now.strftime("%B %d, %Y")

    print()
    print(divider("═"))
    print(f"  WEEKLY INSIGHTS REPORT  |  {week_start} – {week_end}")
    print(divider("═"))
    print(f"  Posts with analytics: {len(posts)}")
    print()

    # Top 5
    top5 = top_5_by_engagement(posts)
    print(divider())
    print("  TOP 5 POSTS BY ENGAGEMENT RATE")
    print(divider())
    if not top5:
        print("  No posts with engagement rate data found.")
    else:
        for i, p in enumerate(top5, 1):
            name = p["name"][:45] + "…" if len(p["name"]) > 45 else p["name"]
            print(f"  {i}. {name}")
            print(
                f"     Platform: {p['platform']:<12}  Date: {p['date'] or '—'}"
            )
            eng = p["engagements"]
            eng_display = f"{int(eng):,}" if isinstance(eng, (int, float)) and eng == int(eng) else f"{eng:,.0f}"
            print(
                f"     Engagement Rate: {pct(p['engagement_rate']):<10}  "
                f"Impressions: {p['impressions']:,}  "
                f"Engagements: {eng_display}"
            )
            print()

    # Platform breakdown
    avg_by_platform = avg_engagement_by_platform(posts)
    print(divider())
    print("  AVERAGE ENGAGEMENT RATE BY PLATFORM")
    print(divider())
    if not avg_by_platform:
        print("  No platform data found.")
    else:
        for platform, avg in sorted(
            avg_by_platform.items(), key=lambda x: x[1], reverse=True
        ):
            bar_len = int(avg * 1000)  # scale for display
            bar = "█" * min(bar_len, 40)
            print(f"  {platform:<14}  {pct(avg):<8}  {bar}")
        print()

    print(divider("═"))
    print("  Report generated:", now.strftime("%Y-%m-%d %H:%M"))
    print(divider("═"))
    print()


def main() -> None:
    api_key = os.getenv("AIRTABLE_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("ERROR: Set AIRTABLE_API_KEY in your .env file.")
        print("  cp .env.template .env  # then add your key")
        raise SystemExit(1)

    print("Fetching posts from Airtable…")
    posts = fetch_posts_with_analytics(api_key)

    if not posts:
        print("No posts with analytics data found.")
        raise SystemExit(0)

    print_report(posts)


if __name__ == "__main__":
    main()
