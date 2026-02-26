"""
Export QB data — blended 2024+2025 seasons (2025=60%, 2024=40%).
Includes: rushing EPA, win %, high-leverage EPA, GWD, YPA in composite.

Run from project root:
    PYTHONPATH=. python src/data/export_dashboard_data.py
"""

import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "dashboard" / "src" / "data"

TEAM_ABBR_FIX = {"LA": "LAR", "JAC": "JAX", "OAK": "LV", "STL": "LAR", "SD": "LAC"}

WEIGHT_2025 = 0.60
WEIGHT_2024 = 0.40
MIN_GAMES = 10
MIN_ATTEMPTS = 200


def compute_season_stats(df, season_label=""):
    throws = df[(df["sack"] == 0) & (df["qb_scramble"] == 0)].copy()
    dropbacks = df[df["qb_dropback"] == 1].copy()

    stats = df.groupby("passer_player_id").agg(
        name=("passer_player_name", "first"),
        team=("posteam", lambda x: x.mode().iloc[0]),
        games=("game_id", "nunique"),
    )
    stats["team"] = stats["team"].replace(TEAM_ABBR_FIX)

    # ── Core passing stats ──
    stats["epa"] = df.groupby("passer_player_id")["epa"].mean()
    stats["total_epa"] = df.groupby("passer_player_id")["epa"].sum()

    throw_stats = throws.groupby("passer_player_id").agg(
        comp_pct=("complete_pass", "mean"),
        pass_yds=("yards_gained", "sum"),
        pass_td=("touchdown", "sum"),
        interceptions=("interception", "sum"),
        attempts=("play_id", "count"),
    )
    stats = stats.join(throw_stats)
    stats["comp_pct"] = stats["comp_pct"] * 100

    cpoe = throws[throws["cpoe"].notna()].groupby("passer_player_id")["cpoe"].mean()
    stats["cpoe"] = cpoe

    # ── Yards per attempt (on throws only, not sacks) ──
    ypa = throws.groupby("passer_player_id")["yards_gained"].sum() / throws.groupby("passer_player_id")["play_id"].count()
    stats["ypa"] = ypa

    sack_stats = dropbacks.groupby("passer_player_id").agg(
        sacks=("sack", "sum"), total_dropbacks=("play_id", "count"),
    )
    sack_stats["sack_rate"] = sack_stats["sacks"] / sack_stats["total_dropbacks"] * 100
    stats["sack_rate"] = sack_stats["sack_rate"]

    stats["avg_air_yards"] = throws.groupby("passer_player_id")["air_yards"].mean()
    stats["deep_ball_rate"] = throws.groupby("passer_player_id")["air_yards"].apply(
        lambda x: (x >= 20).mean() * 100
    )
    stats["int_rate"] = stats["interceptions"] / stats["attempts"].clip(lower=1) * 100
    stats["td_rate"] = stats["pass_td"] / stats["attempts"].clip(lower=1) * 100

    # ── Rushing stats ──
    scrambles = df[df["qb_scramble"] == 1]
    rush = scrambles.groupby("passer_player_id").agg(
        rush_yds=("yards_gained", "sum"), rush_td=("touchdown", "sum"),
        scramble_epa=("epa", "sum"),
    )
    stats = stats.join(rush, how="left")
    stats["rush_yds"] = stats["rush_yds"].fillna(0).astype(int)
    stats["rush_td"] = stats["rush_td"].fillna(0).astype(int)
    stats["scramble_epa"] = stats["scramble_epa"].fillna(0)

    # Designed rushes
    stats["designed_rush_epa"] = 0.0
    for season in [2024, 2025]:
        raw_path = RAW_DIR / f"play_by_play_{season}.parquet"
        if not raw_path.exists():
            continue
        raw = pd.read_parquet(raw_path)
        season_qbs = df[df["season"] == season]["passer_player_id"].unique() if "season" in df.columns else stats.index
        qb_rushes = raw[
            (raw["play_type"] == "run") & (raw["season_type"] == "REG")
            & (raw["rusher_player_id"].isin(season_qbs)) & (raw["qb_scramble"] == 0)
        ]
        dr = qb_rushes.groupby("rusher_player_id").agg(
            dr_yds=("yards_gained", "sum"), dr_td=("touchdown", "sum"), dr_epa=("epa", "sum"),
        )
        dr.index.name = "passer_player_id"
        for idx in dr.index:
            if idx in stats.index:
                stats.loc[idx, "rush_yds"] = int(stats.loc[idx, "rush_yds"]) + int(dr.loc[idx, "dr_yds"])
                stats.loc[idx, "rush_td"] = int(stats.loc[idx, "rush_td"]) + int(dr.loc[idx, "dr_td"])
                stats.loc[idx, "designed_rush_epa"] = float(stats.loc[idx, "designed_rush_epa"]) + float(dr.loc[idx, "dr_epa"])

    stats["rush_epa_total"] = stats["scramble_epa"] + stats["designed_rush_epa"]
    stats["rush_epa_per_game"] = stats["rush_epa_total"] / stats["games"].clip(lower=1)

    # ── Win % as starter ──
    # Determine winner of each game, then compute win % per QB
    game_results = df.groupby(["passer_player_id", "game_id"]).agg(
        posteam=("posteam", "first"),
        home_team=("home_team", "first"),
        away_team=("away_team", "first"),
    ).reset_index()

    # We need score data — use the last play's score differential proxy
    # Actually, use WPA: if a QB's total WPA in a game is associated with a win
    # Simpler: get final score from play-by-play
    game_wpa = df.groupby(["passer_player_id", "game_id"]).agg(
        total_wpa=("wpa", "sum"),
        posteam=("posteam", "first"),
    ).reset_index()

    # Use total game EPA as a proxy — positive total EPA strongly correlates with winning
    game_epa = df.groupby(["passer_player_id", "game_id"])["epa"].sum().reset_index()
    game_epa.columns = ["passer_player_id", "game_id", "game_epa"]

    # Better approach: check if team won using score differential at end of game
    last_plays = df.sort_values("play_id").groupby(["passer_player_id", "game_id"]).last().reset_index()

    if "score_differential" in last_plays.columns:
        last_plays["won"] = last_plays["score_differential"] > 0
        win_pct = last_plays.groupby("passer_player_id")["won"].mean()
        stats["win_pct"] = win_pct * 100
        wins = last_plays.groupby("passer_player_id")["won"].sum()
        losses = last_plays.groupby("passer_player_id")["won"].count() - wins
        stats["wins"] = wins.astype(int)
        stats["losses"] = (losses).astype(int)
    else:
        stats["win_pct"] = 50.0
        stats["wins"] = 0
        stats["losses"] = 0

    # ── High-leverage EPA ──
    # High leverage = win probability between 20% and 80% (game is competitive)
    if "wp" in df.columns:
        high_lev = df[(df["wp"] >= 0.20) & (df["wp"] <= 0.80)]
        stats["high_leverage_epa"] = high_lev.groupby("passer_player_id")["epa"].mean()
    else:
        stats["high_leverage_epa"] = stats["epa"]

    # ── 4th quarter comebacks / game-winning drives ──
    # GWD proxy: 4th quarter or OT, team is trailing or tied, and QB's plays produce positive EPA
    gwd_plays = df[
        (df["qtr"] >= 4)
        & (df["score_differential"] <= 0)
    ]
    # Count games where QB had positive EPA in these situations AND the final score_diff was positive
    gwd_game = gwd_plays.groupby(["passer_player_id", "game_id"]).agg(
        gwd_epa=("epa", "sum"),
        gwd_plays=("play_id", "count"),
    ).reset_index()

    # Merge with game outcome
    if "score_differential" in last_plays.columns:
        game_outcomes = last_plays[["passer_player_id", "game_id", "score_differential"]].copy()
        game_outcomes.columns = ["passer_player_id", "game_id", "final_diff"]
        gwd_game = gwd_game.merge(game_outcomes, on=["passer_player_id", "game_id"], how="left")
        # A GWD = QB was trailing in 4th, produced positive EPA, and team won
        gwd_game["is_gwd"] = (gwd_game["gwd_epa"] > 0) & (gwd_game["final_diff"] > 0)
        gwd_counts = gwd_game.groupby("passer_player_id")["is_gwd"].sum()
        stats["gwd"] = gwd_counts.astype(int)
        # GWD EPA = average EPA in comeback situations
        gwd_epa_avg = gwd_plays.groupby("passer_player_id")["epa"].mean()
        stats["gwd_epa"] = gwd_epa_avg
    else:
        stats["gwd"] = 0
        stats["gwd_epa"] = 0

    # ── Pressure ──
    if "was_pressure" in df.columns and df["was_pressure"].notna().any():
        pt = throws[throws["was_pressure"].notna()]
        stats["epa_pressured"] = pt[pt["was_pressure"] == 1].groupby("passer_player_id")["epa"].mean()
        stats["epa_clean"] = pt[pt["was_pressure"] == 0].groupby("passer_player_id")["epa"].mean()
        stats["pressure_resilience"] = stats["epa_pressured"] - stats["epa_clean"]

    # ── Clutch ──
    clutch = df[(df["qtr"] == 4) & (df["score_differential"].abs() <= 8)]
    clutch_n = clutch.groupby("passer_player_id")["play_id"].count()
    stats["clutch_epa"] = clutch.groupby("passer_player_id")["epa"].mean()
    low_clutch = clutch_n[clutch_n < 15].index
    stats.loc[stats.index.isin(low_clutch), "clutch_epa"] = np.nan

    stats["neg_play_rate"] = df.groupby("passer_player_id")["epa"].apply(lambda x: (x < 0).mean() * 100)
    stats["success_rate"] = df.groupby("passer_player_id")["epa"].apply(lambda x: (x > 0).mean() * 100)

    logger.info(f"  {season_label}: {len(stats)} QBs")
    return stats


def blend_seasons(stats_2024, stats_2025):
    qual_24 = set(stats_2024[stats_2024["games"] >= MIN_GAMES].index)
    qual_25 = set(stats_2025[stats_2025["games"] >= MIN_GAMES].index)
    all_qbs = qual_24 | qual_25

    dropped = ((set(stats_2024.index) | set(stats_2025.index)) - all_qbs)
    if dropped:
        names = []
        for qb in dropped:
            if qb in stats_2025.index: names.append(stats_2025.loc[qb, "name"])
            elif qb in stats_2024.index: names.append(stats_2024.loc[qb, "name"])
        logger.info(f"  Filtered out {len(dropped)} QBs (<{MIN_GAMES} games): {', '.join(sorted(names))}")

    logger.info(f"Blending {len(all_qbs)} qualifying QBs")

    rate_cols = [
        "epa", "cpoe", "comp_pct", "sack_rate", "avg_air_yards", "deep_ball_rate",
        "int_rate", "td_rate", "neg_play_rate", "success_rate",
        "epa_pressured", "epa_clean", "pressure_resilience", "clutch_epa",
        "rush_epa_per_game", "win_pct", "high_leverage_epa", "gwd_epa", "ypa",
    ]
    count_cols = [
        "pass_yds", "pass_td", "interceptions", "rush_yds", "rush_td",
        "total_epa", "attempts", "games", "sacks", "rush_epa_total",
        "wins", "losses", "gwd",
    ]

    blended = pd.DataFrame(index=list(all_qbs))

    for qb in all_qbs:
        if qb in stats_2025.index:
            blended.loc[qb, "name"] = stats_2025.loc[qb, "name"]
            blended.loc[qb, "team"] = stats_2025.loc[qb, "team"]
        else:
            blended.loc[qb, "name"] = stats_2024.loc[qb, "name"]
            blended.loc[qb, "team"] = stats_2024.loc[qb, "team"]

    for col in rate_cols:
        for qb in all_qbs:
            has_24 = qb in stats_2024.index and qb in qual_24 and col in stats_2024.columns and pd.notna(stats_2024.loc[qb].get(col))
            has_25 = qb in stats_2025.index and qb in qual_25 and col in stats_2025.columns and pd.notna(stats_2025.loc[qb].get(col))
            if has_24 and has_25:
                blended.loc[qb, col] = stats_2025.loc[qb, col] * WEIGHT_2025 + stats_2024.loc[qb, col] * WEIGHT_2024
            elif has_25:
                blended.loc[qb, col] = stats_2025.loc[qb, col]
            elif has_24:
                blended.loc[qb, col] = stats_2024.loc[qb, col]
            else:
                blended.loc[qb, col] = np.nan

    for col in count_cols:
        for qb in all_qbs:
            val = 0
            if qb in stats_2024.index and qb in qual_24 and col in stats_2024.columns:
                v = stats_2024.loc[qb].get(col, 0)
                if pd.notna(v): val += v
            if qb in stats_2025.index and qb in qual_25 and col in stats_2025.columns:
                v = stats_2025.loc[qb].get(col, 0)
                if pd.notna(v): val += v
            blended.loc[qb, col] = val

    for col in count_cols:
        if col in blended.columns:
            blended[col] = pd.to_numeric(blended[col], errors="coerce").fillna(0).astype(int)

    for qb in all_qbs:
        in_24 = qb in qual_24
        in_25 = qb in qual_25
        blended.loc[qb, "seasons"] = "2024-2025" if (in_24 and in_25) else ("2025" if in_25 else "2024")

    return blended


def compute_composite_rating(stats):
    """
    Composite rating with 4 new metrics:
    - win_pct: rewards winners (Mahomes), punishes losers (Carr)
    - high_leverage_epa: performance when game is competitive
    - gwd_epa: comeback/game-winning drive EPA
    - ypa: yards per attempt (efficiency + aggression)
    """
    weights = {
        "epa": 0.18,                # Passing efficiency
        "cpoe": 0.08,               # Accuracy over expected
        "total_epa": 0.05,          # Volume
        "success_rate": 0.06,       # Consistency
        "rush_epa_per_game": 0.10,  # Rushing value
        "win_pct": 0.12,            # WINNING (big for Mahomes, bad for Carr)
        "high_leverage_epa": 0.10,  # Clutch in competitive games
        "gwd_epa": 0.05,            # Comeback ability
        "ypa": 0.06,                # Yards per attempt
        "td_rate": 0.03,            # Scoring
        "int_rate": -0.06,          # Turnovers
        "sack_rate": -0.05,         # Sack avoidance
        "neg_play_rate": -0.06,     # Floor plays
    }

    scores = pd.DataFrame(index=stats.index)
    for metric, weight in weights.items():
        if metric not in stats.columns:
            continue
        vals = pd.to_numeric(stats[metric], errors="coerce")
        vals = vals.fillna(vals.median())
        pctile = vals.rank(pct=True)
        if weight < 0:
            pctile = 1 - pctile
            weight = abs(weight)
        scores[metric] = pctile * weight

    raw = scores.sum(axis=1)
    mn, mx = raw.min(), raw.max()
    if mx > mn:
        return (40 + (raw - mn) / (mx - mn) * 59).round(0).astype(int)
    return pd.Series(70, index=stats.index)


def assign_tiers(stats):
    ratings = stats["rating"]
    e = ratings.quantile(0.88)
    b = ratings.quantile(0.70)
    s = ratings.quantile(0.35)
    def t(r):
        if r >= e: return "Elite"
        if r >= b: return "Blue Chip"
        if r >= s: return "Quality Starter"
        return "Bridge / Backup"
    tiers = ratings.apply(t)
    for tier in ["Elite", "Blue Chip", "Quality Starter", "Bridge / Backup"]:
        logger.info(f"  {tier}: {(tiers == tier).sum()} QBs")
    return tiers


def assign_badges(stats):
    badges_list = []
    pctiles = {}
    for col in ["epa", "cpoe", "avg_air_yards", "rush_yds", "sack_rate",
                 "comp_pct", "int_rate", "clutch_epa", "deep_ball_rate",
                 "pressure_resilience", "neg_play_rate", "success_rate",
                 "rush_epa_per_game", "win_pct", "high_leverage_epa", "ypa"]:
        if col in stats.columns:
            vals = pd.to_numeric(stats[col], errors="coerce")
            pctiles[col] = vals.rank(pct=True)

    for idx, row in stats.iterrows():
        badges = []
        p = {c: pctiles[c].get(idx, 0.5) if idx in pctiles[c].index else 0.5 for c in pctiles}

        rush = float(row.get("rush_yds", 0) or 0)
        pyds = float(row.get("pass_yds", 0) or 0)

        # Positive
        if rush > 600: badges.append("Dual Threat")
        elif rush > 300: badges.append("Mobile")
        if p.get("avg_air_yards", 0.5) > 0.80: badges.append("Gunslinger")
        elif p.get("avg_air_yards", 0.5) > 0.65: badges.append("Aggressive")
        if p.get("cpoe", 0.5) > 0.75: badges.append("Accurate")
        if p.get("high_leverage_epa", 0.5) > 0.80: badges.append("Clutch")
        if p.get("win_pct", 0.5) > 0.80: badges.append("Winner")
        if p.get("pressure_resilience", 0.5) > 0.75: badges.append("Composed")
        if p.get("epa", 0.5) > 0.80: badges.append("Efficient")
        if p.get("rush_epa_per_game", 0.5) > 0.85: badges.append("Dynamic Runner")
        if rush < 200: badges.append("Pocket Passer")
        if pyds > 7000: badges.append("Volume")
        if p.get("ypa", 0.5) > 0.80: badges.append("Big Play")

        # Negative
        if p.get("cpoe", 0.5) < 0.20: badges.append("Inaccurate")
        if p.get("int_rate", 0.5) > 0.75: badges.append("Turnover Prone")
        if p.get("sack_rate", 0.5) > 0.80: badges.append("Holds Ball")
        if p.get("avg_air_yards", 0.5) < 0.20: badges.append("Conservative")
        if p.get("epa", 0.5) < 0.20: badges.append("Struggling")
        if p.get("win_pct", 0.5) < 0.25: badges.append("Losing Record")
        if p.get("neg_play_rate", 0.5) > 0.75 and "Struggling" not in badges: badges.append("Inconsistent")

        neg_set = {"Inaccurate", "Turnover Prone", "Holds Ball", "Struggling",
                   "Inconsistent", "Conservative", "Losing Record"}
        pos = [b for b in badges if b not in neg_set]
        neg = [b for b in badges if b in neg_set]
        rating = float(row.get("rating", 70) or 70)
        final = (pos + neg)[:3] if rating >= 75 else (pos[:1] + neg + pos[1:])[:3]
        if not final:
            final = ["Steady"] if float(row.get("epa", 0) or 0) > 0.05 else ["Developing"]
        badges_list.append(final)

    return pd.Series(badges_list, index=stats.index)


def clean_nans(obj):
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return 0
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nans(v) for v in obj]
    return obj


def export_data():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(message)s")

    path = PROCESSED_DIR / "pass_plays_qualified.parquet"
    if not path.exists():
        logger.error("Run data pipeline first: PYTHONPATH=. python -m src.data.load_data")
        return

    df = pd.read_parquet(path)
    logger.info(f"Loaded {len(df):,} total plays")

    seasons = sorted(df["season"].unique()) if "season" in df.columns else [2025]
    logger.info(f"Seasons available: {seasons}")

    if len(seasons) >= 2 and 2024 in seasons and 2025 in seasons:
        logger.info("Computing blended 2024-2025 stats...")
        stats_2024 = compute_season_stats(df[df["season"] == 2024], "2024")
        stats_2025 = compute_season_stats(df[df["season"] == 2025], "2025")
        stats = blend_seasons(stats_2024, stats_2025)
    else:
        logger.info("Single season mode...")
        stats = compute_season_stats(df, str(seasons[0]))
        stats = stats[stats["games"] >= MIN_GAMES]

    # Filter low-volume QBs
    stats = stats[pd.to_numeric(stats["attempts"], errors="coerce").fillna(0) >= MIN_ATTEMPTS]
    logger.info(f"After min attempts filter: {len(stats)} QBs")

    stats["rating"] = compute_composite_rating(stats)
    stats["tier"] = assign_tiers(stats)
    stats["badges"] = assign_badges(stats)
    stats = stats.sort_values("rating", ascending=False)
    stats["rank"] = range(1, len(stats) + 1)

    qb_list = []
    for _, row in stats.iterrows():
        qb_list.append({
            "rank": int(row["rank"]), "name": row["name"], "team": row["team"],
            "tier": row["tier"], "rating": int(row["rating"]),
            "epa": round(float(row.get("epa") or 0), 3),
            "cpoe": round(float(row.get("cpoe") or 0), 1),
            "compPct": round(float(row.get("comp_pct") or 0), 1),
            "passYds": int(row.get("pass_yds") or 0),
            "passTd": int(row.get("pass_td") or 0),
            "int": int(row.get("interceptions") or 0),
            "sackRate": round(float(row.get("sack_rate") or 0), 1),
            "avgAirYards": round(float(row.get("avg_air_yards") or 0), 1),
            "deepBallRate": round(float(row.get("deep_ball_rate") or 0), 1),
            "rushYds": int(row.get("rush_yds") or 0),
            "rushTd": int(row.get("rush_td") or 0),
            "rushEpaPerGame": round(float(row.get("rush_epa_per_game") or 0), 2),
            "winPct": round(float(row.get("win_pct") or 0), 1),
            "wins": int(row.get("wins") or 0),
            "losses": int(row.get("losses") or 0),
            "highLeverageEpa": round(float(row.get("high_leverage_epa") or 0), 3),
            "gwd": int(row.get("gwd") or 0),
            "ypa": round(float(row.get("ypa") or 0), 1),
            "clutchEpa": round(float(row.get("clutch_epa") or 0), 3),
            "negPlayRate": round(float(row.get("neg_play_rate") or 0), 1),
            "badges": row["badges"],
            "seasons": row.get("seasons", "2025"),
        })

    qb_list = clean_nans(qb_list)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "qb_data.json", "w") as f:
        json.dump(qb_list, f, indent=2)

    logger.info(f"Exported {len(qb_list)} QBs")

    print(f"\n{'='*90}")
    print(f"  QB Intelligence — Blended 2024-2025 (min {MIN_GAMES}g, {MIN_ATTEMPTS}att)")
    print(f"{'='*90}")
    print(f"{'Rk':<4}{'Name':<20}{'Tm':<5}{'Tier':<18}{'RTG':<5}{'EPA':<8}{'Win%':<6}{'HiLev':<8}{'RshEPA':<8}{'Badges'}")
    print(f"{'-'*90}")
    for qb in qb_list:
        print(f"{qb['rank']:<4}{qb['name']:<20}{qb['team']:<5}{qb['tier']:<18}{qb['rating']:<5}"
              f"{qb['epa']:>+.3f} {qb['winPct']:>5.1f} {qb['highLeverageEpa']:>+.3f}  "
              f"{qb['rushEpaPerGame']:>+.2f}    {', '.join(qb['badges'])}")


if __name__ == "__main__":
    export_data()
