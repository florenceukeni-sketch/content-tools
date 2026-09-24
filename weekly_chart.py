"""Generate an HTML visual report from Airtable Posts analytics."""

import os
import subprocess
import json
from collections import defaultdict
from datetime import datetime, timedelta

from dotenv import load_dotenv
from pyairtable import Api

load_dotenv()

BASE_ID = "app5LdHmUEycVYeh1"
TABLE_ID = "tbl8L67GarvyY05ZI"


def fetch_posts(api_key: str) -> list[dict]:
    api = Api(api_key)
    table = api.table(BASE_ID, TABLE_ID)
    records = table.all(
        fields=[
            "Name", "Date", "Platform",
            "Impressions", "Engagements", "Clicks",
            "Engagement Rate", "CTR", "Month",
        ],
        formula="NOT({Impressions} = '')",
    )
    posts = []
    for r in records:
        f = r["fields"]
        posts.append({
            "name": f.get("Name", "(untitled)"),
            "date": f.get("Date", ""),
            "platform": f.get("Platform", "Unknown"),
            "impressions": int(f.get("Impressions", 0)),
            "engagements": int(f.get("Engagements", 0) or 0),
            "clicks": int(f.get("Clicks", 0) or 0),
            "engagement_rate": f.get("Engagement Rate"),
            "ctr": f.get("CTR"),
            "month": f.get("Month", ""),
        })
    return posts


def top_n(posts: list[dict], n: int = 5) -> list[dict]:
    ranked = [p for p in posts if p["engagement_rate"] is not None]
    ranked.sort(key=lambda p: p["engagement_rate"], reverse=True)
    return ranked[:n]


def avg_by_platform(posts: list[dict]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for p in posts:
        if p["engagement_rate"] is not None:
            buckets[p["platform"]].append(p["engagement_rate"])
    return {k: sum(v) / len(v) for k, v in buckets.items()}


def overall_avg(posts: list[dict]) -> float:
    rates = [p["engagement_rate"] for p in posts if p["engagement_rate"] is not None]
    return sum(rates) / len(rates) if rates else 0.0


def build_html(posts: list[dict]) -> str:
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).strftime("%B %-d")
    week_end = now.strftime("%B %-d, %Y")

    top5 = top_n(posts, 5)
    avg_rate = overall_avg(posts)
    platforms = avg_by_platform(posts)
    platform_str = ", ".join(platforms.keys()) or "—"

    max_rate = top5[0]["engagement_rate"] if top5 else 1.0

    # Build bar rows
    bar_rows = ""
    for p in top5:
        rate = p["engagement_rate"]
        pct_val = rate * 100
        bar_width = (rate / max_rate) * 100

        short_name = p["name"][:52] + "…" if len(p["name"]) > 52 else p["name"]
        imp = f"{p['impressions']:,}"
        eng = f"{p['engagements']:,}"
        clicks = f"{p['clicks']:,}"
        ctr_str = f"{p['ctr']*100:.2f}%" if p["ctr"] else "—"
        date_str = p["date"] or "—"

        tooltip_data = json.dumps({
            "name": p["name"],
            "date": date_str,
            "platform": p["platform"],
            "impressions": imp,
            "engagements": eng,
            "clicks": clicks,
            "ctr": ctr_str,
            "rate": f"{pct_val:.2f}%",
        })

        bar_rows += f"""
        <div class="bar-row" data-tooltip='{tooltip_data}'>
          <div class="bar-label" title="{p['name']}">{short_name}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:{bar_width:.2f}%"></div>
            <span class="bar-value">{pct_val:.2f}%</span>
          </div>
        </div>"""

    # Platform platform tiles
    platform_tiles = ""
    for plat, avg in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
        platform_tiles += f"""
        <div class="stat-tile">
          <div class="stat-label">{plat} Avg Engagement</div>
          <div class="stat-value">{avg*100:.2f}%</div>
        </div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Weekly Insights · {week_start}–{week_end}</title>
<style>
  .viz-root {{
    color-scheme: light;
    --surface-1:       #fcfcfb;
    --surface-page:    #f9f9f7;
    --text-primary:    #0b0b0b;
    --text-secondary:  #52514e;
    --text-muted:      #898781;
    --gridline:        #e1e0d9;
    --baseline:        #c3c2b7;
    --series-1:        #2a78d6;
    --series-1-light:  #cde2fb;
    --border:          rgba(11,11,11,0.10);
  }}
  @media (prefers-color-scheme: dark) {{
    .viz-root {{
      color-scheme: dark;
      --surface-1:       #1a1a19;
      --surface-page:    #0d0d0d;
      --text-primary:    #ffffff;
      --text-secondary:  #c3c2b7;
      --text-muted:      #898781;
      --gridline:        #2c2c2a;
      --baseline:        #383835;
      --series-1:        #3987e5;
      --series-1-light:  #1c5cab;
      --border:          rgba(255,255,255,0.10);
    }}
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: var(--surface-page);
    color: var(--text-primary);
    padding: 32px 24px;
    min-height: 100vh;
  }}

  .viz-root {{
    max-width: 760px;
    margin: 0 auto;
  }}

  /* Header */
  .report-header {{
    margin-bottom: 28px;
  }}
  .report-title {{
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.02em;
  }}
  .report-subtitle {{
    font-size: 0.8125rem;
    color: var(--text-muted);
    margin-top: 4px;
  }}

  /* KPI row */
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 28px;
  }}
  .stat-tile {{
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
  }}
  .stat-label {{
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
  }}
  .stat-value {{
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.03em;
    line-height: 1;
  }}
  .stat-sub {{
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-top: 4px;
  }}

  /* Chart card */
  .chart-card {{
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 16px;
  }}
  .chart-title {{
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 20px;
  }}

  /* Bar chart */
  .bar-row {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
    position: relative;
    cursor: default;
  }}
  .bar-row:last-child {{ margin-bottom: 0; }}

  .bar-label {{
    flex: 0 0 220px;
    font-size: 0.8125rem;
    color: var(--text-secondary);
    text-align: right;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .bar-track {{
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    position: relative;
    height: 28px;
  }}
  .bar-fill {{
    height: 100%;
    background: var(--series-1);
    border-radius: 0 4px 4px 0;
    transition: opacity 0.15s;
    min-width: 2px;
  }}
  .bar-row:hover .bar-fill {{
    opacity: 0.82;
  }}
  .bar-value {{
    font-size: 0.8125rem;
    font-variant-numeric: tabular-nums;
    color: var(--text-primary);
    font-weight: 600;
    white-space: nowrap;
  }}

  /* Tooltip */
  .tooltip {{
    display: none;
    position: fixed;
    z-index: 100;
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 6px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    padding: 12px 14px;
    font-size: 0.8125rem;
    max-width: 280px;
    pointer-events: none;
  }}
  .tooltip.visible {{ display: block; }}
  .tooltip-name {{
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
    line-height: 1.4;
  }}
  .tooltip-row {{
    display: flex;
    justify-content: space-between;
    gap: 16px;
    color: var(--text-secondary);
    margin-bottom: 3px;
  }}
  .tooltip-row span:last-child {{
    font-variant-numeric: tabular-nums;
    color: var(--text-primary);
    font-weight: 500;
  }}
  .tooltip-divider {{
    height: 1px;
    background: var(--gridline);
    margin: 8px 0;
  }}

  .footer {{
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 16px;
  }}
</style>
</head>
<body>
<div class="viz-root">
  <div class="report-header">
    <div class="report-title">Weekly Insights</div>
    <div class="report-subtitle">{week_start} – {week_end} &nbsp;·&nbsp; CAAI Social Media</div>
  </div>

  <div class="kpi-row">
    <div class="stat-tile">
      <div class="stat-label">Posts with Analytics</div>
      <div class="stat-value">{len(posts)}</div>
      <div class="stat-sub">LinkedIn</div>
    </div>
    <div class="stat-tile">
      <div class="stat-label">Avg Engagement Rate</div>
      <div class="stat-value">{avg_rate*100:.2f}%</div>
      <div class="stat-sub">across all tracked posts</div>
    </div>
    <div class="stat-tile">
      <div class="stat-label">Top Post Rate</div>
      <div class="stat-value">{top5[0]['engagement_rate']*100:.2f}%</div>
      <div class="stat-sub">{(top5[0]['name'][:30] + '…') if len(top5[0]['name']) > 30 else top5[0]['name']}</div>
    </div>
  </div>

  <div class="chart-card">
    <div class="chart-title">Top 5 Posts by Engagement Rate</div>
    {bar_rows}
  </div>

  <div class="footer">Generated {now.strftime("%Y-%m-%d %H:%M")} &nbsp;·&nbsp; Airtable base app5LdHmUEycVYeh1</div>
</div>

<div class="tooltip" id="tooltip">
  <div class="tooltip-name" id="tt-name"></div>
  <div class="tooltip-row"><span>Platform</span><span id="tt-platform"></span></div>
  <div class="tooltip-row"><span>Date</span><span id="tt-date"></span></div>
  <div class="tooltip-divider"></div>
  <div class="tooltip-row"><span>Engagement Rate</span><span id="tt-rate"></span></div>
  <div class="tooltip-row"><span>Impressions</span><span id="tt-impressions"></span></div>
  <div class="tooltip-row"><span>Engagements</span><span id="tt-engagements"></span></div>
  <div class="tooltip-row"><span>Clicks</span><span id="tt-clicks"></span></div>
  <div class="tooltip-row"><span>CTR</span><span id="tt-ctr"></span></div>
</div>

<script>
  const tooltip = document.getElementById('tooltip');
  const rows = document.querySelectorAll('.bar-row[data-tooltip]');

  rows.forEach(row => {{
    const data = JSON.parse(row.dataset.tooltip);

    row.addEventListener('mouseenter', e => {{
      document.getElementById('tt-name').textContent = data.name;
      document.getElementById('tt-platform').textContent = data.platform;
      document.getElementById('tt-date').textContent = data.date;
      document.getElementById('tt-rate').textContent = data.rate;
      document.getElementById('tt-impressions').textContent = data.impressions;
      document.getElementById('tt-engagements').textContent = data.engagements;
      document.getElementById('tt-clicks').textContent = data.clicks;
      document.getElementById('tt-ctr').textContent = data.ctr;
      tooltip.classList.add('visible');
      positionTooltip(e);
    }});

    row.addEventListener('mousemove', positionTooltip);
    row.addEventListener('mouseleave', () => tooltip.classList.remove('visible'));
  }});

  function positionTooltip(e) {{
    const pad = 14;
    const tw = tooltip.offsetWidth;
    const th = tooltip.offsetHeight;
    let x = e.clientX + pad;
    let y = e.clientY + pad;
    if (x + tw > window.innerWidth - pad) x = e.clientX - tw - pad;
    if (y + th > window.innerHeight - pad) y = e.clientY - th - pad;
    tooltip.style.left = x + 'px';
    tooltip.style.top  = y + 'px';
  }}
</script>
</body>
</html>"""


def main() -> None:
    api_key = os.getenv("AIRTABLE_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("ERROR: Set AIRTABLE_API_KEY in your .env file.")
        raise SystemExit(1)

    print("Fetching posts from Airtable…")
    posts = fetch_posts(api_key)

    if not posts:
        print("No posts with analytics data found.")
        raise SystemExit(0)

    html = build_html(posts)
    out_path = os.path.join(os.path.dirname(__file__), "insights_report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report written to {out_path}")
    subprocess.run(["open", out_path])


if __name__ == "__main__":
    main()
