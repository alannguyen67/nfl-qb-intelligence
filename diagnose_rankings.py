"""
Diagnostic: print detailed stats for problem QBs to understand ranking issues.
Run: PYTHONPATH=. python diagnose_rankings.py
"""
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(".")
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR = PROJECT_ROOT / "data" / "raw"

df = pd.read_parquet(PROCESSED_DIR / "pass_plays_qualified.parquet")

# Focus QBs
focus = ["J.Daniels", "P.Mahomes", "J.Love", "J.Goff", "D.Carr", "J.Allen", "L.Jackson", "J.Hurts", "J.Burrow"]

for season in [2024, 2025]:
    sdf = df[df["season"] == season]
    throws = sdf[(sdf["sack"] == 0) & (sdf["qb_scramble"] == 0)]
    
    print(f"\n{'='*100}")
    print(f"  {season} SEASON — RAW STATS")
    print(f"{'='*100}")
    print(f"{'Name':<15}{'Games':<7}{'Att':<6}{'EPA/play':<10}{'CPOE':<8}{'Comp%':<8}{'YPA':<7}{'TD':<5}{'INT':<5}{'Sack%':<7}{'Win%':<7}{'HiLevEPA':<10}")
    print(f"{'-'*100}")
    
    for name in focus:
        qb_plays = sdf[sdf["passer_player_name"] == name]
        qb_throws = throws[throws["passer_player_name"] == name]
        
        if len(qb_plays) == 0:
            print(f"{name:<15} — NOT IN {season}")
            continue
        
        games = qb_plays["game_id"].nunique()
        attempts = len(qb_throws)
        epa = qb_plays["epa"].mean()
        cpoe = qb_throws[qb_throws["cpoe"].notna()]["cpoe"].mean() if qb_throws["cpoe"].notna().any() else 0
        comp = qb_throws["complete_pass"].mean() * 100
        ypa = qb_throws["yards_gained"].sum() / max(len(qb_throws), 1)
        td = qb_throws["touchdown"].sum()
        ints = qb_throws["interception"].sum()
        dropbacks = qb_plays[qb_plays["qb_dropback"] == 1]
        sack_rate = dropbacks["sack"].mean() * 100 if len(dropbacks) > 0 else 0
        
        # Win %
        last = qb_plays.sort_values("play_id").groupby("game_id").last()
        win_pct = (last["score_differential"] > 0).mean() * 100
        
        # High leverage EPA
        hi_lev = qb_plays[(qb_plays["wp"] >= 0.20) & (qb_plays["wp"] <= 0.80)]
        hi_lev_epa = hi_lev["epa"].mean() if len(hi_lev) > 0 else 0
        
        # Rush stats
        scrambles = qb_plays[qb_plays["qb_scramble"] == 1]
        scramble_yds = scrambles["yards_gained"].sum()
        
        raw_path = RAW_DIR / f"play_by_play_{season}.parquet"
        design_rush_yds = 0
        if raw_path.exists():
            raw = pd.read_parquet(raw_path)
            pid = qb_plays["passer_player_id"].iloc[0]
            dr = raw[(raw["play_type"] == "run") & (raw["rusher_player_id"] == pid) 
                     & (raw["qb_scramble"] == 0) & (raw["season_type"] == "REG")]
            design_rush_yds = dr["yards_gained"].sum()
        
        total_rush = scramble_yds + design_rush_yds
        
        print(f"{name:<15}{games:<7}{attempts:<6}{epa:<+10.3f}{cpoe:<+8.1f}{comp:<8.1f}{ypa:<7.1f}{td:<5}{ints:<5}{sack_rate:<7.1f}{win_pct:<7.1f}{hi_lev_epa:<+10.3f}  rush:{total_rush}")

print(f"\n\n{'='*100}")
print("KEY OBSERVATIONS:")
print("='*100")
print("Compare Derek Carr vs Jayden Daniels — what metrics is Carr winning on?")
print("Compare Jordan Love vs Patrick Mahomes — what's inflating Love?")
print("This will tell us exactly what to fix.\n")
