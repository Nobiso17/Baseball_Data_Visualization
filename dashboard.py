"""
Baseball Analytics Dashboard — Lahman Database
Generates a multi-panel visualization from warehouse mart tables.
Run pipeline.py first to build the warehouse.
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import numpy as np

WH_DB = "warehouse.db"

# ── Theme ─────────────────────────────────────────────────────────────────────
BG       = "#0d1117"
PANEL_BG = "#161b22"
BORDER   = "#30363d"
TEXT     = "#e6edf3"
MUTED    = "#8b949e"
RED      = "#f85149"
BLUE     = "#58a6ff"
GREEN    = "#3fb950"
GOLD     = "#d29922"
PURPLE   = "#bc8cff"

plt.rcParams.update({
    "figure.facecolor":  BG,
    "axes.facecolor":    PANEL_BG,
    "axes.edgecolor":    BORDER,
    "axes.labelcolor":   MUTED,
    "xtick.color":       MUTED,
    "ytick.color":       MUTED,
    "text.color":        TEXT,
    "grid.color":        BORDER,
    "grid.linestyle":    "--",
    "grid.alpha":        0.5,
    "font.family":       "monospace",
    "font.size":         9,
})

def load(table):
    con = sqlite3.connect(WH_DB)
    df = pd.read_sql(f"SELECT * FROM {table}", con)
    con.close()
    return df

def panel_title(ax, title):
    ax.set_title(title, color=TEXT, fontsize=10, fontweight="bold", pad=10, loc="left")

# ── Plot 1: MLB Average Salary Growth (1985–2016) ────────────────────────────
def plot_salary_growth(ax):
    df = load("mart_salary_by_year")
    ax.plot(df["yearID"], df["avg_salary_millions"], color=GREEN, linewidth=2)
    ax.fill_between(df["yearID"], df["avg_salary_millions"], alpha=0.15, color=GREEN)

    # Annotate key events
    events = {1994: "Strike", 2002: "CBA", 2011: "CBA"}
    for yr, label in events.items():
        row = df[df["yearID"] == yr]
        if not row.empty:
            y = row["avg_salary_millions"].values[0]
            ax.axvline(yr, color=MUTED, linewidth=0.8, linestyle=":")
            ax.text(yr + 0.3, y + 0.1, label, color=MUTED, fontsize=7)

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.1f}M"))
    ax.set_xlabel("Year")
    ax.grid(True, axis="y")
    panel_title(ax, "MLB Average Salary Growth  1985 – 2016")

# ── Plot 2: All-Time HR Leaders (top 15) ─────────────────────────────────────
def plot_hr_leaders(ax):
    df = load("mart_hr_leaders").head(15).sort_values("career_hr")
    colors = [RED if hr >= 700 else BLUE for hr in df["career_hr"]]
    bars = ax.barh(df["player_name"], df["career_hr"], color=colors, height=0.65)

    for bar, val in zip(bars, df["career_hr"]):
        ax.text(val + 3, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=8, color=TEXT)

    ax.set_xlabel("Career Home Runs")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    legend = [mpatches.Patch(color=RED, label="700+ HR"),
              mpatches.Patch(color=BLUE, label="< 700 HR")]
    ax.legend(handles=legend, fontsize=7, facecolor=PANEL_BG, edgecolor=BORDER,
              labelcolor=TEXT)
    ax.grid(True, axis="x")
    panel_title(ax, "All-Time Home Run Leaders")

# ── Plot 3: ERA Leaders — career (top 20 lowest ERA, min 1000 IP) ────────────
def plot_era_leaders(ax):
    df = load("mart_career_pitching").head(20).sort_values("era", ascending=False)
    colors = [GREEN if e < 2.5 else BLUE if e < 3.0 else GOLD for e in df["era"]]
    bars = ax.barh(df["player_name"], df["era"], color=colors, height=0.65)

    for bar, val in zip(bars, df["era"]):
        ax.text(val + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}", va="center", fontsize=8, color=TEXT)

    ax.set_xlabel("Career ERA")
    legend = [mpatches.Patch(color=GREEN, label="< 2.50"),
              mpatches.Patch(color=BLUE,  label="2.50 – 3.00"),
              mpatches.Patch(color=GOLD,  label="> 3.00")]
    ax.legend(handles=legend, fontsize=7, facecolor=PANEL_BG, edgecolor=BORDER,
              labelcolor=TEXT)
    ax.grid(True, axis="x")
    panel_title(ax, "Career ERA Leaders  (min 1,000 IP, since 1920)")

# ── Plot 4: Batting Avg vs HR — HOF batters scatter ──────────────────────────
def plot_hof_scatter(ax):
    df = load("mart_hof_batters").dropna(subset=["batting_avg", "career_hr"])
    df = df[df["career_hr"] > 0]

    sc = ax.scatter(
        df["career_hr"], df["batting_avg"],
        c=df["career_hits"], cmap="plasma",
        s=45, alpha=0.75, edgecolors=BORDER, linewidths=0.4,
    )

    # Label outliers
    for _, row in df[df["career_hr"] >= 500].iterrows():
        ax.annotate(row["player_name"].split()[-1],
                    (row["career_hr"], row["batting_avg"]),
                    fontsize=6.5, color=TEXT,
                    xytext=(4, 2), textcoords="offset points")

    cbar = plt.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label("Career Hits", color=MUTED, fontsize=8)
    cbar.ax.yaxis.set_tick_params(color=MUTED)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=MUTED, fontsize=7)

    ax.set_xlabel("Career Home Runs")
    ax.set_ylabel("Career Batting Average")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f".{int(x*1000):03d}"))
    ax.grid(True)
    panel_title(ax, "HOF Batters — HR vs Batting Avg  (color = career hits)")

# ── Plot 5: Win % by decade — top 5 franchises ───────────────────────────────
def plot_franchise_wins(ax):
    df = load("mart_team_wins_by_decade")
    df = df[df["decade"] >= 1950]

    # Top 5 franchises by total wins since 1950
    top_franchises = (
        df.groupby("franchID")["total_wins"]
        .sum().nlargest(5).index.tolist()
    )
    palette = [BLUE, RED, GREEN, GOLD, PURPLE]

    for franch, color in zip(top_franchises, palette):
        sub = df[df["franchID"] == franch].sort_values("decade")
        label = sub["team_name"].iloc[-1]   # most recent name
        ax.plot(sub["decade"], sub["win_pct"], marker="o", markersize=4,
                color=color, linewidth=1.8, label=label)

    ax.axhline(0.5, color=MUTED, linewidth=0.8, linestyle=":")
    ax.text(1952, 0.501, ".500", color=MUTED, fontsize=7)
    ax.set_xlabel("Decade")
    ax.set_ylabel("Win %")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.3f}"))
    ax.legend(fontsize=7, facecolor=PANEL_BG, edgecolor=BORDER, labelcolor=TEXT)
    ax.grid(True)
    panel_title(ax, "Win % by Decade — Top 5 Franchises  (since 1950)")

# ── Plot 6: Summary stat cards ────────────────────────────────────────────────
def plot_stat_cards(ax):
    ax.axis("off")
    con = sqlite3.connect(WH_DB)
    stats = {
        "Players (1950+,\n1000+ AB)":
            f"{con.execute('SELECT COUNT(*) FROM mart_career_batting').fetchone()[0]:,}",
        "All-Time HR\nLeader":
            con.execute("SELECT player_name FROM mart_hr_leaders LIMIT 1").fetchone()[0],
        "Avg MLB Salary\n(2016)":
            f"$4.40M",
        "HOF Batters\nin dataset":
            f"{con.execute('SELECT COUNT(*) FROM mart_hof_batters').fetchone()[0]:,}",
        "Career ERA\nLeader (post-1920)":
            con.execute("SELECT player_name FROM mart_career_pitching ORDER BY era LIMIT 1").fetchone()[0],
        "Years of\nSalary Data":
            "1985 – 2016",
    }
    con.close()

    cols, rows = 3, 2
    for i, (label, value) in enumerate(stats.items()):
        col = i % cols
        row = i // cols
        x = col / cols + 0.02
        y = 1 - row / rows - 0.08

        # Card background
        rect = mpatches.FancyBboxPatch(
            (x, y - 0.36), 0.3, 0.38,
            boxstyle="round,pad=0.02",
            linewidth=1, edgecolor=BORDER,
            facecolor="#1f2937",
            transform=ax.transAxes, clip_on=False,
        )
        ax.add_patch(rect)
        ax.text(x + 0.15, y - 0.02, value, ha="center", va="top",
                fontsize=10, fontweight="bold", color=BLUE,
                transform=ax.transAxes)
        ax.text(x + 0.15, y - 0.22, label, ha="center", va="top",
                fontsize=7.5, color=MUTED, transform=ax.transAxes)

    panel_title(ax, "At a Glance")

# ── Assemble ──────────────────────────────────────────────────────────────────
def main():
    fig = plt.figure(figsize=(18, 13))
    fig.patch.set_facecolor(BG)

    # Header
    fig.text(0.5, 0.975, "Baseball Analytics Dashboard — Lahman Database",
             ha="center", va="top", fontsize=15, fontweight="bold", color=TEXT)
    fig.text(0.5, 0.957, "1871 – 2019  |  107,429 batting records  |  47,628 pitching records",
             ha="center", va="top", fontsize=9, color=MUTED)

    gs = fig.add_gridspec(3, 3, hspace=0.42, wspace=0.32,
                          left=0.07, right=0.97, top=0.93, bottom=0.05)

    ax1 = fig.add_subplot(gs[0, :2])   # salary growth — wide
    ax2 = fig.add_subplot(gs[0, 2])    # stat cards
    ax3 = fig.add_subplot(gs[1, 0])    # HR leaders
    ax4 = fig.add_subplot(gs[1, 1])    # ERA leaders
    ax5 = fig.add_subplot(gs[1, 2])    # HOF scatter
    ax6 = fig.add_subplot(gs[2, :])    # franchise wins — full width

    plot_salary_growth(ax1)
    plot_stat_cards(ax2)
    plot_hr_leaders(ax3)
    plot_era_leaders(ax4)
    plot_hof_scatter(ax5)
    plot_franchise_wins(ax6)

    out = "data/output/dashboard.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"Dashboard saved → {out}")

if __name__ == "__main__":
    main()
