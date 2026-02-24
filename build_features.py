"""
Feature engineering for QB play style analysis.

Transforms play-level data into per-QB aggregated metrics that capture
different dimensions of quarterback play style and performance.

Metrics:
    - Aggression Index: Deep ball tendency and average air yards
    - Pressure Resilience: Performance delta under pressure vs. clean pocket
    - Decisiveness Score: Sack avoidance and quick-release tendency
    - Clutch Factor: Performance in high-leverage situations
    - Mobility Score: Scramble tendency and rushing effectiveness
    - Accuracy Profile: Completion rates by pass depth and location
"""

import logging

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Individual metric builders
# ──────────────────────────────────────────────────────────────────────


def compute_aggression_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Measure how aggressively a QB pushes the ball downfield.

    Features:
        - avg_air_yards: Mean intended air yards per attempt
        - deep_ball_rate: Percentage of throws with 20+ air yards
        - avg_intended_epa: Mean EPA on all pass attempts (not just completions)
    """
    agg = df.groupby("passer_player_id").agg(
        avg_air_yards=("air_yards", "mean"),
        deep_ball_rate=("air_yards", lambda x: (x >= 20).mean()),
        avg_intended_epa=("epa", "mean"),
        passer_name=("passer_player_name", "first"),
    )
    return agg[["avg_air_yards", "deep_ball_rate", "avg_intended_epa"]]


def compute_pressure_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Measure QB performance under pressure vs. clean pocket.

    Features:
        - epa_clean: EPA per play from a clean pocket
        - epa_pressure: EPA per play under pressure
        - pressure_resilience: Difference (smaller gap = more resilient)
        - completion_pct_pressure: Completion rate under pressure
    """
    if "was_pressure" not in df.columns or df["was_pressure"].isna().all():
        logger.warning("Pressure data not available — returning NaN columns")
        qbs = df.groupby("passer_player_id").size().index
        return pd.DataFrame(
            {
                "epa_clean": np.nan,
                "epa_pressure": np.nan,
                "pressure_resilience": np.nan,
                "completion_pct_pressure": np.nan,
            },
            index=qbs,
        )

    # Exclude sacks for a cleaner signal on actual throw quality
    throws = df[df["sack"] == 0].copy()

    clean = throws[throws["was_pressure"] == 0]
    pressured = throws[throws["was_pressure"] == 1]

    epa_clean = clean.groupby("passer_player_id")["epa"].mean().rename("epa_clean")
    epa_pressure = pressured.groupby("passer_player_id")["epa"].mean().rename("epa_pressure")
    comp_pressure = (
        pressured.groupby("passer_player_id")["complete_pass"]
        .mean()
        .rename("completion_pct_pressure")
    )

    pressure_df = pd.concat([epa_clean, epa_pressure, comp_pressure], axis=1)
    pressure_df["pressure_resilience"] = (
        pressure_df["epa_pressure"] - pressure_df["epa_clean"]
    )
    # Less negative = more resilient, so higher is better
    return pressure_df


def compute_decisiveness_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Measure how quickly and decisively a QB operates.

    Features:
        - sack_rate: Percentage of dropbacks resulting in a sack
        - scramble_rate: Percentage of dropbacks resulting in a scramble
    """
    dropbacks = df[df["qb_dropback"] == 1]

    agg = dropbacks.groupby("passer_player_id").agg(
        sack_rate=("sack", "mean"),
        scramble_rate=("qb_scramble", "mean"),
        total_dropbacks=("play_id", "count"),
    )
    return agg[["sack_rate", "scramble_rate"]]


def compute_clutch_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Measure QB performance in high-leverage situations.

    High-leverage = 4th quarter with score differential within 8 points.

    Features:
        - clutch_epa: EPA per play in high-leverage situations
        - clutch_completion_pct: Completion rate in high-leverage
        - clutch_play_share: What % of a QB's plays are in high-leverage spots
    """
    clutch_mask = (df["qtr"] == 4) & (df["score_differential"].abs() <= 8)

    all_plays = df.groupby("passer_player_id")["play_id"].count().rename("total_plays")
    clutch_plays = df[clutch_mask].copy()

    clutch_agg = clutch_plays.groupby("passer_player_id").agg(
        clutch_epa=("epa", "mean"),
        clutch_completion_pct=("complete_pass", "mean"),
        clutch_play_count=("play_id", "count"),
    )

    clutch_agg = clutch_agg.join(all_plays)
    clutch_agg["clutch_play_share"] = clutch_agg["clutch_play_count"] / clutch_agg["total_plays"]

    return clutch_agg[["clutch_epa", "clutch_completion_pct", "clutch_play_share"]]


def compute_mobility_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Measure QB mobility and rushing contribution on pass plays.

    Features:
        - scramble_rate: (also in decisiveness, included for clustering)
        - scramble_yards_per_attempt: Avg yards gained on scrambles
        - designed_rush_rate: Rate of designed QB runs (if distinguishable)
    """
    dropbacks = df[df["qb_dropback"] == 1]

    scrambles = dropbacks[dropbacks["qb_scramble"] == 1]
    scramble_yards = (
        scrambles.groupby("passer_player_id")["yards_gained"]
        .mean()
        .rename("scramble_yards_per_attempt")
    )

    scramble_rate = (
        dropbacks.groupby("passer_player_id")["qb_scramble"]
        .mean()
        .rename("scramble_rate_mobility")
    )

    return pd.concat([scramble_rate, scramble_yards], axis=1).fillna(0)


def compute_accuracy_profile(df: pd.DataFrame) -> pd.DataFrame:
    """
    Break down completion rates by pass depth zone.

    Features:
        - comp_pct_short: Completion % on throws < 10 air yards
        - comp_pct_medium: Completion % on throws 10-19 air yards
        - comp_pct_deep: Completion % on throws 20+ air yards
        - overall_comp_pct: Overall completion percentage
    """
    throws = df[df["sack"] == 0].copy()

    # Bin by air yards
    throws["depth_zone"] = pd.cut(
        throws["air_yards"],
        bins=[-np.inf, 10, 20, np.inf],
        labels=["short", "medium", "deep"],
    )

    overall = throws.groupby("passer_player_id")["complete_pass"].mean().rename("overall_comp_pct")

    depth_comp = (
        throws.groupby(["passer_player_id", "depth_zone"])["complete_pass"]
        .mean()
        .unstack(fill_value=np.nan)
    )
    depth_comp.columns = [f"comp_pct_{c}" for c in depth_comp.columns]

    return depth_comp.join(overall)


# ──────────────────────────────────────────────────────────────────────
# Main feature builder
# ──────────────────────────────────────────────────────────────────────


def build_qb_features(pass_plays: pd.DataFrame) -> pd.DataFrame:
    """
    Build the full QB feature matrix by computing all metric groups
    and joining them together.

    Args:
        pass_plays: Cleaned play-level DataFrame (from load_data pipeline)

    Returns:
        DataFrame with one row per qualifying QB and all engineered features.
    """
    logger.info("Building QB feature matrix...")

    # Compute each metric group
    aggression = compute_aggression_metrics(pass_plays)
    pressure = compute_pressure_metrics(pass_plays)
    decisiveness = compute_decisiveness_metrics(pass_plays)
    clutch = compute_clutch_metrics(pass_plays)
    mobility = compute_mobility_metrics(pass_plays)
    accuracy = compute_accuracy_profile(pass_plays)

    # Get QB name mapping
    name_map = (
        pass_plays.groupby("passer_player_id")["passer_player_name"]
        .first()
        .rename("player_name")
    )
    attempt_counts = (
        pass_plays.groupby("passer_player_id")
        .size()
        .rename("pass_attempts")
    )
    team_map = (
        pass_plays.groupby("passer_player_id")["posteam"]
        .agg(lambda x: x.mode().iloc[0])
        .rename("team")
    )

    # Join everything
    features = (
        name_map.to_frame()
        .join(team_map)
        .join(attempt_counts)
        .join(aggression)
        .join(pressure)
        .join(decisiveness)
        .join(clutch)
        .join(mobility)
        .join(accuracy)
    )

    logger.info(f"Feature matrix: {features.shape[0]} QBs × {features.shape[1]} features")
    return features


def get_clustering_features(features: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Extract and standardize the numeric features used for clustering.

    Returns:
        Tuple of (scaled DataFrame, list of feature column names)
    """
    # Select numeric columns only (exclude name, team, attempt count)
    exclude_cols = ["player_name", "team", "pass_attempts"]
    feature_cols = [c for c in features.columns if c not in exclude_cols]

    X = features[feature_cols].copy()

    # Fill any remaining NaN with column median
    X = X.fillna(X.median())

    # Standardize
    scaler = StandardScaler()
    X_scaled = pd.DataFrame(
        scaler.fit_transform(X),
        index=X.index,
        columns=X.columns,
    )

    logger.info(f"Clustering features: {len(feature_cols)} dimensions")
    return X_scaled, feature_cols
