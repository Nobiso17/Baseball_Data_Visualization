"""
Baseball Analytics Pipeline — Lahman Database
Transforms raw Lahman SQLite data into analytics-ready mart tables.
Covers: batting stats, career leaders, salary analysis, team performance, Hall of Fame.
"""

import sqlite3
import shutil
import pandas as pd
from pathlib import Path

SRC_DB  = "data/raw/lahman.sqlite"
WH_DB   = "warehouse.db"
OUT_DIR = Path("data/output")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def src():
    return sqlite3.connect(SRC_DB)

def wh():
    return sqlite3.connect(WH_DB)

def run(con, sql: str):
    con.executescript(sql)
    con.commit()

# ── Stage: copy raw tables into warehouse ─────────────────────────────────────

STAGE_TABLES = ["batting", "pitching", "people", "teams", "salaries",
                "halloffame", "awardsplayers"]

def stage():
    print("Staging raw tables…")
    shutil.copy2(SRC_DB, WH_DB)   # start from a copy of the source
    print(f"  Copied {SRC_DB} → {WH_DB}")
    for t in STAGE_TABLES:
        count = wh().execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count:,} rows")

# ── Transform: build mart tables ──────────────────────────────────────────────

TRANSFORMS = {

    # ── Batting: career totals for players with 1000+ AB (modern era 1950+) ──
    "mart_career_batting": """
        DROP TABLE IF EXISTS mart_career_batting;
        CREATE TABLE mart_career_batting AS
        SELECT
            b.playerID,
            p.nameFirst || ' ' || p.nameLast          AS player_name,
            MIN(b.yearID)                              AS debut_year,
            MAX(b.yearID)                              AS final_year,
            COUNT(DISTINCT b.yearID)                   AS seasons,
            SUM(b.G)                                   AS games,
            SUM(b.AB)                                  AS at_bats,
            SUM(b.H)                                   AS hits,
            SUM(b.HR)                                  AS home_runs,
            SUM(b.RBI)                                 AS rbi,
            SUM(b.BB)                                  AS walks,
            SUM(b.SO)                                  AS strikeouts,
            SUM(b."2B")                                AS doubles,
            SUM(b."3B")                                AS triples,
            SUM(b.SB)                                  AS stolen_bases,
            ROUND(CAST(SUM(b.H) AS FLOAT)
                  / NULLIF(SUM(b.AB), 0), 3)           AS batting_avg,
            ROUND(CAST(SUM(b.H) + SUM(b.BB) AS FLOAT)
                  / NULLIF(SUM(b.AB) + SUM(b.BB), 0), 3) AS obp,
            ROUND(CAST(
                  SUM(b.H) + SUM(b."2B") + 2*SUM(b."3B") + 3*SUM(b.HR)
                  AS FLOAT) / NULLIF(SUM(b.AB), 0), 3) AS slg
        FROM batting b
        JOIN people p USING (playerID)
        WHERE b.yearID >= 1950
        GROUP BY b.playerID
        HAVING SUM(b.AB) >= 1000
        ORDER BY home_runs DESC;
    """,

    # ── All-time HR leaders (top 50) ─────────────────────────────────────────
    "mart_hr_leaders": """
        DROP TABLE IF EXISTS mart_hr_leaders;
        CREATE TABLE mart_hr_leaders AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY SUM(b.HR) DESC) AS rank,
            p.nameFirst || ' ' || p.nameLast            AS player_name,
            SUM(b.HR)                                   AS career_hr,
            ROUND(CAST(SUM(b.H) AS FLOAT)
                  / NULLIF(SUM(b.AB), 0), 3)            AS batting_avg,
            COUNT(DISTINCT b.yearID)                    AS seasons
        FROM batting b
        JOIN people p USING (playerID)
        GROUP BY b.playerID
        HAVING SUM(b.AB) >= 500
        ORDER BY career_hr DESC
        LIMIT 50;
    """,

    # ── Salary analysis: avg salary by year (1985–2016) ──────────────────────
    "mart_salary_by_year": """
        DROP TABLE IF EXISTS mart_salary_by_year;
        CREATE TABLE mart_salary_by_year AS
        SELECT
            yearID,
            COUNT(DISTINCT playerID)            AS players_with_salary,
            ROUND(AVG(salary), 0)               AS avg_salary,
            ROUND(MIN(salary), 0)               AS min_salary,
            ROUND(MAX(salary), 0)               AS max_salary,
            ROUND(AVG(salary) / 1000000.0, 2)   AS avg_salary_millions
        FROM salaries
        GROUP BY yearID
        ORDER BY yearID;
    """,

    # ── Top 25 highest single-season salaries ────────────────────────────────
    "mart_top_salaries": """
        DROP TABLE IF EXISTS mart_top_salaries;
        CREATE TABLE mart_top_salaries AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY s.salary DESC) AS rank,
            p.nameFirst || ' ' || p.nameLast           AS player_name,
            s.teamID                                   AS team,
            s.yearID                                   AS year,
            s.salary,
            ROUND(s.salary / 1000000.0, 2)             AS salary_millions
        FROM salaries s
        JOIN people p USING (playerID)
        ORDER BY s.salary DESC
        LIMIT 25;
    """,

    # ── Team win totals by decade ─────────────────────────────────────────────
    "mart_team_wins_by_decade": """
        DROP TABLE IF EXISTS mart_team_wins_by_decade;
        CREATE TABLE mart_team_wins_by_decade AS
        SELECT
            (yearID / 10) * 10                  AS decade,
            name                                AS team_name,
            franchID,
            SUM(W)                              AS total_wins,
            SUM(L)                              AS total_losses,
            COUNT(*)                            AS seasons_played,
            ROUND(CAST(SUM(W) AS FLOAT)
                  / (SUM(W) + SUM(L)), 3)       AS win_pct,
            SUM(CASE WHEN WSWin = 'Y' THEN 1 ELSE 0 END) AS world_series_wins
        FROM teams
        WHERE yearID >= 1900
        GROUP BY (yearID / 10) * 10, franchID
        ORDER BY decade DESC, total_wins DESC;
    """,

    # ── Hall of Fame inductees with career batting stats ─────────────────────
    "mart_hof_batters": """
        DROP TABLE IF EXISTS mart_hof_batters;
        CREATE TABLE mart_hof_batters AS
        SELECT
            p.nameFirst || ' ' || p.nameLast     AS player_name,
            h.yearID                             AS inducted_year,
            h.category,
            SUM(b.HR)                            AS career_hr,
            SUM(b.H)                             AS career_hits,
            SUM(b.RBI)                           AS career_rbi,
            ROUND(CAST(SUM(b.H) AS FLOAT)
                  / NULLIF(SUM(b.AB), 0), 3)     AS batting_avg,
            COUNT(DISTINCT b.yearID)             AS seasons
        FROM halloffame h
        JOIN people p USING (playerID)
        LEFT JOIN batting b USING (playerID)
        WHERE h.inducted = 'Y'
          AND h.category = 'Player'
        GROUP BY h.playerID
        HAVING SUM(b.AB) >= 500
        ORDER BY career_hr DESC;
    """,

    # ── Pitching: career ERA leaders (min 1000 IP = 3000 outs) ───────────────
    "mart_career_pitching": """
        DROP TABLE IF EXISTS mart_career_pitching;
        CREATE TABLE mart_career_pitching AS
        SELECT
            pi.playerID,
            p.nameFirst || ' ' || p.nameLast       AS player_name,
            MIN(pi.yearID)                          AS debut_year,
            MAX(pi.yearID)                          AS final_year,
            COUNT(DISTINCT pi.yearID)               AS seasons,
            SUM(pi.W)                               AS wins,
            SUM(pi.L)                               AS losses,
            SUM(pi.G)                               AS games,
            SUM(pi.SV)                              AS saves,
            SUM(pi.IPouts)                          AS ip_outs,
            ROUND(SUM(pi.IPouts) / 3.0, 1)          AS innings_pitched,
            SUM(pi.SO)                              AS strikeouts,
            SUM(pi.BB)                              AS walks,
            SUM(pi.HR)                              AS hr_allowed,
            ROUND(CAST(SUM(pi.ER) * 27 AS FLOAT)
                  / NULLIF(SUM(pi.IPouts), 0), 2)   AS era
        FROM pitching pi
        JOIN people p USING (playerID)
        WHERE pi.yearID >= 1920
        GROUP BY pi.playerID
        HAVING SUM(pi.IPouts) >= 3000
        ORDER BY era ASC;
    """,
}


def transform():
    print("\nBuilding mart tables…")
    con = wh()
    for name, sql in TRANSFORMS.items():
        con.executescript(sql)
        count = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"  {name}: {count:,} rows")
    con.commit()
    con.close()


# ── Export ────────────────────────────────────────────────────────────────────

def export():
    print("\nExporting CSVs…")
    con = wh()
    for name in TRANSFORMS:
        df = pd.read_sql(f"SELECT * FROM {name}", con)
        path = OUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"  {path}")
    con.close()


# ── Summary ───────────────────────────────────────────────────────────────────

def summary():
    con = wh()
    top_hr = con.execute(
        "SELECT player_name, career_hr FROM mart_hr_leaders LIMIT 5"
    ).fetchall()
    avg_sal = con.execute(
        "SELECT yearID, avg_salary_millions FROM mart_salary_by_year "
        "WHERE yearID IN (1985, 1995, 2005, 2016)"
    ).fetchall()
    con.close()

    print("\n── All-Time HR Leaders ────────────────────────")
    for i, (name, hr) in enumerate(top_hr, 1):
        print(f"  {i}. {name:<25} {hr:>4} HR")

    print("\n── Average MLB Salary (selected years) ────────")
    for year, sal in avg_sal:
        print(f"  {year}   ${sal:.2f}M")
    print("───────────────────────────────────────────────\n")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Baseball Analytics Pipeline ===\n")
    stage()
    transform()
    export()
    summary()
    print("Pipeline complete. CSVs in data/output/")
