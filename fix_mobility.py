"""
Fix for the mobility scatter plot.

The original scramble_rate_mobility only looked at scrambles on pass plays,
which clusters everyone near zero. This version pulls QB rushing stats from
the full play-by-play data to create a more meaningful mobility metric.

Run from project root:
    PYTHONPATH=. python fix_mobility.py
"""

import pandas as pd
import numpy as np
import nfl_data_py as nfl


def build_better_mobility(season=2025):
    """
    Build a mobility score using BOTH scrambles and designed QB runs.
    
    Combines:
    - Scramble rate (from pass plays)
    - Designed rush rate (QB runs on non-pass plays)
    - Rushing yards per game
    - Rushing EPA per attempt
    """
    print("Loading full play-by-play...")
    pbp = pd.read_parquet('data/raw/play_by_play_2025.parquet')
    pass_plays = pd.read_parquet('data/processed/pass_plays_qualified.parquet')
    
    qualifying_qbs = pass_plays['passer_player_id'].unique()
    
    # --- Scramble data (from pass plays) ---
    dropbacks = pass_plays[pass_plays['qb_dropback'] == 1]
    scramble_stats = dropbacks.groupby('passer_player_id').agg(
        scramble_rate=('qb_scramble', 'mean'),
        scramble_epa=('epa', lambda x: x[dropbacks.loc[x.index, 'qb_scramble'] == 1].mean()),
    )
    
    # --- Designed QB rush data ---
    # These are run plays where the QB is the rusher
    qb_rushes = pbp[
        (pbp['play_type'] == 'run')
        & (pbp['season_type'] == 'REG')
        & (pbp['rusher_player_id'].isin(qualifying_qbs))
        & (pbp['qb_scramble'] == 0)  # Exclude scrambles, we count those above
    ].copy()
    
    rush_stats = qb_rushes.groupby('rusher_player_id').agg(
        designed_rushes=('play_id', 'count'),
        rush_yards=('yards_gained', 'sum'),
        rush_epa_total=('epa', 'sum'),
        rush_epa_per=('epa', 'mean'),
        rush_td=('touchdown', 'sum'),
    )
    rush_stats.index.name = 'passer_player_id'
    
    # --- Total dropbacks for rate calculation ---
    total_dropbacks = dropbacks.groupby('passer_player_id')['play_id'].count().rename('total_dropbacks')
    
    # --- Games played (for per-game stats) ---
    games = pass_plays.groupby('passer_player_id')['game_id'].nunique().rename('games_played')
    
    # --- Combine ---
    mobility = scramble_stats.join(rush_stats, how='left').join(total_dropbacks).join(games)
    mobility = mobility.fillna(0)
    
    # Derived metrics
    mobility['designed_rush_rate'] = mobility['designed_rushes'] / (mobility['total_dropbacks'] + mobility['designed_rushes'])
    mobility['rush_yards_per_game'] = mobility['rush_yards'] / mobility['games_played'].clip(lower=1)
    mobility['total_mobility_rate'] = mobility['scramble_rate'] + mobility['designed_rush_rate']
    
    # Composite mobility score (z-score blend)
    for col in ['scramble_rate', 'designed_rush_rate', 'rush_yards_per_game', 'rush_epa_per']:
        mean = mobility[col].mean()
        std = mobility[col].std()
        if std > 0:
            mobility[f'{col}_z'] = (mobility[col] - mean) / std
        else:
            mobility[f'{col}_z'] = 0
    
    mobility['mobility_score'] = (
        mobility['scramble_rate_z'] * 0.25
        + mobility['designed_rush_rate_z'] * 0.30
        + mobility['rush_yards_per_game_z'] * 0.30
        + mobility['rush_epa_per_z'] * 0.15
    )
    
    print(f"\nMobility scores for {len(mobility)} QBs:")
    
    # Get names
    name_map = pass_plays.groupby('passer_player_id')['passer_player_name'].first()
    mobility = mobility.join(name_map)
    
    print(mobility.nlargest(10, 'mobility_score')[
        ['passer_player_name', 'scramble_rate', 'designed_rush_rate', 
         'rush_yards_per_game', 'mobility_score']
    ].to_string())
    
    # Save
    mobility.to_parquet('data/processed/qb_mobility.parquet')
    print("\nSaved to data/processed/qb_mobility.parquet")
    
    return mobility


if __name__ == '__main__':
    build_better_mobility()
