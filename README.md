# Baseball Data Visualization — Lahman Database

An end-to-end SQL analytics pipeline built on the Lahman Baseball Database (1871–2019). Transforms 107k+ batting records and 47k+ pitching records through a layered warehouse into dashboard-ready mart tables and a multi-panel visualization.

## Architecture

```
Lahman SQLite (raw source)
        │
        ▼
   Warehouse DB (staged copy)
        │
        ├──▶ mart_career_batting       Career totals for 2,362 players (1950+, 1000+ AB)
        ├──▶ mart_hr_leaders           All-time top 50 home run hitters
        ├──▶ mart_salary_by_year       MLB avg/min/max salary 1985–2016
        ├──▶ mart_top_salaries         Top 25 highest single-season salaries
        ├──▶ mart_team_wins_by_decade  Win % and World Series wins by franchise & decade
        ├──▶ mart_hof_batters          Hall of Fame batters with career stats
        └──▶ mart_career_pitching      Career ERA leaders (min 1,000 IP, since 1920)
                    │
                    ▼
            dashboard.png + CSVs
```

## Quick Start

```bash
# 1. Download the Lahman database
# Save to: data/raw/lahman.sqlite
# URL: https://github.com/WebucatorTraining/lahman-baseball-mysql/raw/master/lahmansbaseballdb.sqlite

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the pipeline
python pipeline.py

# 4. Generate the dashboard
python dashboard.py
```

## Mart Tables

| Table | Rows | Description |
|---|---|---|
| `mart_career_batting` | 2,362 | Career totals + AVG/OBP/SLG for qualified hitters since 1950 |
| `mart_hr_leaders` | 50 | All-time home run leaders with batting avg and seasons |
| `mart_salary_by_year` | 32 | League-wide salary stats per year, 1985–2016 |
| `mart_top_salaries` | 25 | Highest single-season salaries in MLB history |
| `mart_team_wins_by_decade` | 270 | Franchise win totals, win %, and WS titles by decade |
| `mart_hof_batters` | 218 | Hall of Famers with HR, hits, RBI, and batting avg |
| `mart_career_pitching` | 978 | Career ERA, W/L, IP, K/BB for qualified starters since 1920 |

## Dashboard Panels

- **Salary Growth** — avg MLB salary 1985–2016 with CBA/strike annotations
- **HR Leaders** — top 15 all-time home run hitters
- **ERA Leaders** — top 20 career ERA (min 1,000 IP)
- **HOF Scatter** — HR vs batting avg for Hall of Fame batters, colored by career hits
- **Franchise Wins** — win % by decade for top 5 franchises since 1950
- **Stat Cards** — at-a-glance summary metrics

## File Structure

```
baseball_pipeline/
├── pipeline.py       # Stage → transform → export
├── dashboard.py      # 6-panel matplotlib dashboard
├── requirements.txt
├── warehouse.db      # Auto-created analytics warehouse
├── data/
│   ├── raw/
│   │   └── lahman.sqlite     ← download manually
│   └── output/
│       ├── mart_*.csv        ← exported mart tables
│       └── dashboard.png     ← generated visualization
└── README.md
```

## Extending

Add a mart to the `TRANSFORMS` dict in `pipeline.py`:

```python
"mart_my_analysis": """
    DROP TABLE IF EXISTS mart_my_analysis;
    CREATE TABLE mart_my_analysis AS
    SELECT ... FROM batting JOIN people USING (playerID) ...
"""
```

It will be automatically exported to CSV on the next run.
