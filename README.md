# content-tools

Python scripts for managing CAAI social media analytics via Airtable.

## Setup

### 1. Airtable API token

Create a Personal Access Token at **airtable.com/create/tokens** with these scopes:

| Scope | Required by |
|---|---|
| `data.records:read` | `weekly_insights.py`, `weekly_chart.py` |
| `data.records:write` | `log_analytics.py` |

Set the token's access to the `content-tools` base (app5LdHmUEycVYeh1).

### 2. Environment file

```bash
cp .env.template .env
# open .env and paste your token as AIRTABLE_API_KEY
```

### 3. Dependencies

```bash
python3 -m pip install pyairtable python-dotenv
```

---

## Scripts

### `weekly_insights.py` — terminal report

Pulls all posts with analytics data and prints a weekly summary:
- Top 5 posts by Engagement Rate
- Average engagement rate by Platform

```bash
python3 weekly_insights.py
```

### `weekly_chart.py` — HTML visual report

Same data as above, rendered as an interactive HTML chart and opened in your browser automatically.

```bash
python3 weekly_chart.py
# opens insights_report.html
```

### `log_analytics.py` — interactive analytics logger

Finds posts where 14-day analytics are due (Analytics Due Date ≤ today, not yet Collected) and walks you through entering data for each one. Updates Airtable in real time and marks each post as ✅ Collected.

```bash
python3 log_analytics.py
```

Fields prompted: Impressions, Clicks, Engagements, Reposts/Share, Followers Gained, Engagement Rate (enter as a percentage, e.g. `5.2` for 5.2%).

Press **s** at any post to skip it without changes.
