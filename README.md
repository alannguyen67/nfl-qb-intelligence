# NFL QB Intelligence

A data-driven quarterback evaluation system that combines play-by-play analytics with a two-pillar composite rating to rank NFL quarterbacks. Built with Python (nflverse data pipeline) and React (interactive dashboard with scatter plots, radar comparisons, and auto-generated scouting reports).

## Live Dashboard

```bash
cd dashboard
npm run dev
# → http://localhost:5173
```

### Three tabs:

**Rankings** — Card-based tier view with expandable QB profiles. Click any QB to see their ESPN headshot, auto-generated scouting description, stat bars, and counting stats. Filter by tier.

**Analytics Lab** — Interactive scatter plot (11 configurable axes), 6-axis radar comparison (select up to 3 QBs), and tier distribution overview. Built with Recharts.

**Badge Glossary** — Full reference grid explaining all 23 play-style badges with color-coded categories.

Dark theme with team color accents, ESPN headshots, JetBrains Mono for data, Outfit for UI text.

## How the Rating Works

Every QB receives a composite rating from 40–99 built on two pillars:

### Pillar 1 — Individual Quality (65%)

Isolates the quarterback's performance from team context:

| Metric | Weight | What It Captures |
|--------|--------|------------------|
| Pressure Resilience | 14% | EPA under pressure vs. clean pocket |
| Throw EPA | 12% | EPA on actual throws, excluding sacks |
| Positive Play Rate | 10% | % of throws producing positive EPA |
| YPA | 7% | Yards per attempt on throws |
| Avg Air Yards | 6% | Downfield aggression |
| INT Rate | -6% | Turnover avoidance (lower is better) |
| Sack Rate | -6% | Ball security / escapability |
| CPOE | 4% | Completion % over expected |

### Pillar 2 — Impact (35%)

Captures total value including rushing and clutch performance:

| Metric | Weight | What It Captures |
|--------|--------|------------------|
| Best-Season High-Leverage EPA | 12% | Clutch EPA in competitive games (WP 20–80%), using QB's best season |
| Rush EPA per Game | 10% | Rushing value from scrambles + designed runs |
| Total EPA | 7% | Cumulative production volume |
| GWD EPA | 4% | EPA in 4th quarter comeback situations |
| TD Rate | 2% | Scoring efficiency |

### Design Decisions

**Win % is excluded from the rating.** It's displayed on QB cards but doesn't affect rank. Win % is too team-dependent — it inflates QBs on good rosters and punishes QBs on bad ones regardless of individual play.

**Best-season high-leverage EPA** is used instead of blended. For QBs with an injury-shortened season, the blended average unfairly penalizes their peak performance.

**Pressure resilience is the heaviest-weighted metric** because it's one of the most QB-specific stats available. O-line quality, scheme, and receiver separation don't help when the pocket collapses.

## Data Pipeline

### Two-Season Blended Approach

Stats are blended across the 2024 and 2025 NFL seasons using games-weighted averaging with a recency bonus:

- Each season's influence is proportional to games played
- 2025 games receive a 1.3x recency multiplier
- If a QB played fewer than 10 games in a season, that season is capped at 25% influence
- QBs must have 2025 data to be ranked (no retired/cut players)
- Minimum 300 pass attempts across qualifying seasons
- Single-season QBs receive a 12% confidence penalty (rating regressed toward league average)

### Qualifying Filters

| Filter | Threshold |
|--------|-----------|
| Games (best season) | ≥ 10 |
| Combined attempts | ≥ 300 |
| Must play in 2025 | Yes |

### Tier Assignment

Tiers are percentile-based across qualifying QBs:

| Tier | Percentile | ~Count |
|------|-----------|--------|
| Elite | Top 12% | 4–5 QBs |
| Blue Chip | Top 30% | 5–7 QBs |
| Quality Starter | Top 65% | 8–10 QBs |
| Bridge / Backup | Bottom 35% | 10–12 QBs |

### Play Style Badges

Each QB receives 2–3 badges based on percentile thresholds:

**Positive:** Dual Threat, Mobile, Gunslinger, Aggressive, Accurate, Clutch, Composed, Efficient, Dynamic Runner, Consistent, Big Play, Volume, Pocket Passer, Winner

**Negative:** Inaccurate, Turnover Prone, Holds Ball, Conservative, Struggling, Losing Record, Inconsistent

**Neutral:** Steady, Developing

High-rated QBs show positive badges first; low-rated QBs lead with negative badges.

### Auto-Generated Scouting Descriptions

Each QB gets a natural-language scouting report generated from their stats. The description covers tier classification, primary strengths and weaknesses (based on stat thresholds), season context with record and EPA, and badge tags. These appear in the expanded profile view on the Rankings tab.

### ESPN Headshots

Player headshots are pulled from ESPN's CDN using manually verified profile IDs:

```
https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{ESPN_ID}.png&w=350&h=254
```

The `ESPN_HEADSHOT_IDS` dictionary in `export_dashboard_data.py` maps nflverse player names to ESPN profile IDs. All 36 IDs were verified against ESPN player profile pages.

## Project Structure

```
nfl-qb-intelligence/
├── data/
│   ├── raw/                          # nflverse play-by-play parquet files
│   └── processed/                    # Filtered and qualified pass plays
├── src/
│   └── data/
│       ├── load_data.py              # Data acquisition (pulls 2024 + 2025 seasons)
│       └── export_dashboard_data.py  # Stats, ratings, tiers, badges, descriptions → JSON
├── dashboard/
│   ├── src/
│   │   ├── App.jsx                   # Main app — Rankings tab + Badge Glossary tab
│   │   ├── AnalyticsLab.jsx          # Analytics Lab tab — scatter plots + radar comparisons
│   │   └── data/
│   │       └── qb_data.json          # Exported QB data (generated by export script)
│   └── package.json
└── README.md
```

## Setup

### Prerequisites

- Python 3.10+ with a virtual environment
- Node.js 18+

### Installation

```bash
# Clone the repo
git clone https://github.com/alannguyen67/nfl-qb-intelligence.git
cd nfl-qb-intelligence

# Python environment
python -m venv venv
source venv/bin/activate
pip install pandas numpy nfl_data_py pyarrow

# Pull data and export
PYTHONPATH=. python -m src.data.load_data
PYTHONPATH=. python src/data/export_dashboard_data.py

# Dashboard
cd dashboard
npm install
npm run dev
```

The dashboard will be available at `http://localhost:5173`.

## Data Source

All play-by-play data comes from [nflverse](https://github.com/nflverse/nflverse-data), the open-source NFL data repository maintained by the nflverse community. Metrics like EPA and CPOE are pre-computed in the nflverse dataset using models developed by Ben Baldwin and Sebastian Carl.

## Acknowledgments

Dashboard design inspired by:
- [The Ringer QB Rankings](https://www.theringer.com) — card-based tier design
- [nfelo.com](https://nfelo.com/qb-rankings) — dark sortable stats tables
- [rbsdm.com](https://rbsdm.com) — Ben Baldwin's EPA scatter plots
- [SumerSports](https://sumersports.com) — clean data filtering
