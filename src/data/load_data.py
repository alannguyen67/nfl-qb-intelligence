"""
Data acquisition and cleaning pipeline for NFL play-by-play data.

Uses nfl_data_py to pull play-by-play data from nflverse, then cleans and
filters to passing plays with relevant columns for QB analysis.

Usage:
    python -m src.data.load_data
"""

import logging
from pathlib import Path

import nfl_data_py as nfl
import pandas as pd

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

# 2025 NFL season (2025-2026)
SEASON = [2025]

# Minimum pass attempts to qualify a QB for analysis
MIN_PASS_ATTEMPTS = 200


def load_play_by_play(seasons: list[int] = SEASON) -> pd.DataFrame:
    """Pull raw play-by-play data from nflverse."""
    logger.info(f"Pulling play-by-play data for seasons: {seasons}")
    pbp = nfl.import_pbp_data(seasons)
    logger.info(f"Loaded {len(pbp):,} total plays")
    return pbp


def load_roster_data(seasons: list[int] = SEASON) -> pd.DataFrame:
    """Pull roster data for player metadata (height, weight, draft info)."""
    logger.info("Pulling roster data")
    rosters = nfl.import_seasonal_rosters(seasons)
    return rosters


def filter_pass_plays(pbp: pd.DataFrame) -> pd.DataFrame:
    """
    Filter play-by-play data to regular season passing plays.

    Removes plays with missing passer info, spikes, and two-point conversions.
    """
    pass_plays = pbp[
        (pbp["play_type"] == "pass")
        & (pbp["season_type"] == "REG")
        & (pbp["two_point_attempt"] == 0)
        & (pbp["passer_player_name"].notna())
        & (pbp["qb_spike"] == 0)
    ].copy()

    logger.info(f"Filtered to {len(pass_plays):,} regular season pass plays")
    return pass_plays


def select_passing_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select relevant columns for QB analysis."""
    columns = [
        # Identifiers
        "game_id", "play_id", "season", "week", "game_date",
        "home_team", "away_team", "posteam", "defteam",

        # Passer info
        "passer_player_id", "passer_player_name",
        "receiver_player_id", "receiver_player_name",

        # Play details
        "down", "ydstogo", "yardline_100", "shotgun", "no_huddle",
        "qb_dropback", "qb_scramble", "pass_location",

        # Pass details
        "air_yards", "yards_after_catch", "pass_length",
        "complete_pass", "incomplete_pass", "interception",
        "yards_gained", "touchdown", "sack",

        # Situational
        "quarter_seconds_remaining", "half_seconds_remaining",
        "game_seconds_remaining", "qtr",
        "score_differential",

        # Advanced (pre-computed by nflverse)
        "ep", "epa", "wp", "wpa", "cpoe",
        "qb_epa",

        # Pressure (if available)
        "was_pressure",
    ]

    available_cols = [c for c in columns if c in df.columns]
    missing_cols = set(columns) - set(available_cols)
    if missing_cols:
        logger.warning(f"Columns not found in data: {missing_cols}")

    return df[available_cols].copy()


def get_qualifying_qbs(pass_plays: pd.DataFrame, min_attempts: int = MIN_PASS_ATTEMPTS) -> list:
    """Return list of passer IDs meeting the minimum attempt threshold."""
    attempt_counts = pass_plays.groupby("passer_player_id").size()
    qualifying = attempt_counts[attempt_counts >= min_attempts].index.tolist()
    logger.info(
        f"{len(qualifying)} QBs meet the {min_attempts}-attempt threshold"
    )
    return qualifying


def run_pipeline() -> pd.DataFrame:
    """
    Run the full data pipeline: load, filter, select, and save.

    Returns the cleaned passing plays DataFrame.
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Load raw data
    pbp = load_play_by_play()
    pbp.to_parquet(RAW_DATA_DIR / "play_by_play_2025.parquet", index=False)

    rosters = load_roster_data()
    rosters.to_parquet(RAW_DATA_DIR / "rosters_2025.parquet", index=False)

    # Step 2: Filter to passing plays
    pass_plays = filter_pass_plays(pbp)

    # Step 3: Select relevant columns
    pass_plays = select_passing_columns(pass_plays)

    # Step 4: Identify qualifying QBs
    qualifying_qbs = get_qualifying_qbs(pass_plays)
    pass_plays_qualified = pass_plays[
        pass_plays["passer_player_id"].isin(qualifying_qbs)
    ].copy()

    # Step 5: Save processed data
    pass_plays.to_parquet(
        PROCESSED_DATA_DIR / "pass_plays_all.parquet", index=False
    )
    pass_plays_qualified.to_parquet(
        PROCESSED_DATA_DIR / "pass_plays_qualified.parquet", index=False
    )

    logger.info(
        f"Pipeline complete. {len(pass_plays_qualified):,} plays from "
        f"{pass_plays_qualified['passer_player_name'].nunique()} qualifying QBs saved."
    )
    return pass_plays_qualified


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    )
    df = run_pipeline()
    print(f"\nDone! Shape: {df.shape}")
    print(f"QBs: {sorted(df['passer_player_name'].unique())}")
