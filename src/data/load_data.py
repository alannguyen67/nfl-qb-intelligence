"""
Data acquisition and cleaning pipeline for NFL play-by-play data.

Pulls 2024 and 2025 seasons for a two-year sample.

Usage:
    PYTHONPATH=. python -m src.data.load_data
"""

import logging
from pathlib import Path

import nfl_data_py as nfl

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

SEASONS = [2024, 2025]
MIN_PASS_ATTEMPTS = 150  # Lower threshold since we want QBs who played in either season
MIN_GAMES = 8            # Minimum games per season to avoid small-sample outliers


def load_play_by_play(seasons=SEASONS):
    logger.info(f"Pulling play-by-play data for seasons: {seasons}")
    pbp = nfl.import_pbp_data(seasons)
    logger.info(f"Loaded {len(pbp):,} total plays")
    return pbp


def filter_pass_plays(pbp):
    pass_plays = pbp[
        (pbp["play_type"] == "pass")
        & (pbp["season_type"] == "REG")
        & (pbp["two_point_attempt"] == 0)
        & (pbp["passer_player_name"].notna())
        & (pbp["qb_spike"] == 0)
    ].copy()
    logger.info(f"Filtered to {len(pass_plays):,} regular season pass plays")
    return pass_plays


def filter_qb_rush_plays(pbp, qualifying_qb_ids):
    """Extract designed QB rush plays (not scrambles — those live in pass plays)."""
    rush_cols = [
        "game_id", "play_id", "season", "week",
        "posteam", "rusher_player_id", "rusher_player_name",
        "yards_gained", "epa", "touchdown", "qb_kneel",
    ]
    available = [c for c in rush_cols if c in pbp.columns]
    mask = (
        (pbp["play_type"] == "run")
        & (pbp["season_type"] == "REG")
        & (pbp["two_point_attempt"] == 0)
        & (pbp["rusher_player_id"].isin(qualifying_qb_ids))
    )
    if "qb_kneel" in pbp.columns:
        mask = mask & (pbp["qb_kneel"] != 1)
    rush_plays = pbp[mask][available].copy()
    logger.info(f"Filtered to {len(rush_plays):,} QB designed rush plays")
    return rush_plays


def select_passing_columns(df):
    columns = [
        "game_id", "play_id", "season", "week", "game_date",
        "home_team", "away_team", "posteam", "defteam",
        "passer_player_id", "passer_player_name",
        "receiver_player_id", "receiver_player_name",
        "down", "ydstogo", "yardline_100", "shotgun", "no_huddle",
        "qb_dropback", "qb_scramble", "pass_location",
        "air_yards", "yards_after_catch", "pass_length",
        "complete_pass", "incomplete_pass", "interception",
        "yards_gained", "touchdown", "sack",
        "quarter_seconds_remaining", "half_seconds_remaining",
        "game_seconds_remaining", "qtr",
        "score_differential",
        "ep", "epa", "wp", "wpa", "cpoe", "qb_epa",
        "was_pressure",
    ]
    available = [c for c in columns if c in df.columns]
    missing = set(columns) - set(available)
    if missing:
        logger.warning(f"Columns not found: {missing}")
    return df[available].copy()


def get_qualifying_qbs(pass_plays, min_attempts=MIN_PASS_ATTEMPTS, min_games=MIN_GAMES):
    """Qualify based on attempts AND minimum games played in EITHER season.

    The games filter removes small-sample outliers like Carr/Mariota whose
    inflated per-play rates come from only a handful of games.
    """
    per_season = pass_plays.groupby(["passer_player_id", "season"]).agg(
        attempts=("play_id", "count"),
        games=("game_id", "nunique"),
    ).reset_index()

    qualifying = per_season[
        (per_season["attempts"] >= min_attempts) &
        (per_season["games"] >= min_games)
    ]["passer_player_id"].unique().tolist()

    logger.info(
        f"{len(qualifying)} QBs meet the {min_attempts}-attempt / "
        f"{min_games}-game threshold in at least one season"
    )
    return qualifying


def run_pipeline():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load raw data
    pbp = load_play_by_play()
    for season in SEASONS:
        season_data = pbp[pbp["season"] == season]
        pbp_path = RAW_DATA_DIR / f"play_by_play_{season}.parquet"
        season_data.to_parquet(pbp_path, index=False)
        logger.info(f"Saved {len(season_data):,} plays for {season}")

    # Also save combined raw
    pbp.to_parquet(RAW_DATA_DIR / "play_by_play_combined.parquet", index=False)

    # Filter to passing plays
    pass_plays = filter_pass_plays(pbp)
    pass_plays = select_passing_columns(pass_plays)

    # Identify qualifying QBs (min attempts + min games — drops Carr/Mariota-style outliers)
    qualifying_qbs = get_qualifying_qbs(pass_plays)
    pass_plays_qualified = pass_plays[
        pass_plays["passer_player_id"].isin(qualifying_qbs)
    ].copy()

    # Extract designed QB rush plays for qualifying QBs (used for rushing EPA)
    qb_rush_plays = filter_qb_rush_plays(pbp, qualifying_qbs)

    # Save
    pass_plays.to_parquet(PROCESSED_DATA_DIR / "pass_plays_all.parquet", index=False)
    pass_plays_qualified.to_parquet(PROCESSED_DATA_DIR / "pass_plays_qualified.parquet", index=False)
    qb_rush_plays.to_parquet(PROCESSED_DATA_DIR / "qb_rush_plays_qualified.parquet", index=False)
    logger.info(f"Saved {len(qb_rush_plays):,} QB rush plays for {qb_rush_plays['rusher_player_id'].nunique()} QBs")

    # Also save per-season for granular analysis
    for season in SEASONS:
        season_qualified = pass_plays_qualified[pass_plays_qualified["season"] == season]
        season_qualified.to_parquet(
            PROCESSED_DATA_DIR / f"pass_plays_qualified_{season}.parquet", index=False
        )
        logger.info(f"{season}: {len(season_qualified):,} plays, {season_qualified['passer_player_name'].nunique()} QBs")

    logger.info(
        f"Pipeline complete. {len(pass_plays_qualified):,} total plays from "
        f"{pass_plays_qualified['passer_player_name'].nunique()} qualifying QBs across {SEASONS}."
    )
    return pass_plays_qualified


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    )
    df = run_pipeline()
    print(f"\nDone! Shape: {df.shape}")
    print(f"Seasons: {sorted(df['season'].unique())}")
    print(f"QBs: {sorted(df['passer_player_name'].unique())}")
