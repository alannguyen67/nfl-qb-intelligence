"""
Completion Probability Model — XGBoost classifier predicting pass completions.

Predicts the probability a pass will be completed given situational features,
then computes Completion Percentage Over Expected (CPOE) per QB.

CPOE is a real metric used in NFL analytics: it measures how much a QB
outperforms the expected completion rate given their pass difficulty.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


# Features used for completion probability prediction
MODEL_FEATURES = [
    "air_yards",
    "down",
    "ydstogo",
    "yardline_100",
    "shotgun",
    "no_huddle",
    "score_differential",
    "qtr",
    "half_seconds_remaining",
]

# Optional features (included if available)
OPTIONAL_FEATURES = [
    "was_pressure",
    "pass_location_left",
    "pass_location_middle",
    "pass_location_right",
]


def prepare_model_data(pass_plays: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Prepare features and target for the completion probability model.

    Filters to actual throw attempts (no sacks, scrambles) and
    creates binary target variable.

    Returns:
        Tuple of (feature DataFrame, target Series)
    """
    # Only actual throws
    throws = pass_plays[
        (pass_plays["sack"] == 0)
        & (pass_plays["qb_scramble"] == 0)
        & (pass_plays["air_yards"].notna())
    ].copy()

    # One-hot encode pass location
    if "pass_location" in throws.columns:
        location_dummies = pd.get_dummies(throws["pass_location"], prefix="pass_location")
        throws = pd.concat([throws, location_dummies], axis=1)

    # Target
    y = throws["complete_pass"].astype(int)

    # Select features
    feature_cols = MODEL_FEATURES.copy()
    for f in OPTIONAL_FEATURES:
        if f in throws.columns and throws[f].notna().mean() > 0.5:
            feature_cols.append(f)

    X = throws[feature_cols].copy()

    # Fill missing values
    X = X.fillna(X.median())

    logger.info(f"Model data: {len(X):,} throws, {len(feature_cols)} features")
    logger.info(f"Completion rate: {y.mean():.1%}")

    return X, y


def train_completion_model(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    """
    Train an XGBoost completion probability model.

    Returns dict containing:
        - model: trained XGBClassifier
        - X_test, y_test: held-out test data
        - metrics: evaluation metrics
        - feature_names: list of feature names
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=10,
        eval_metric="logloss",
        random_state=random_state,
        use_label_encoder=False,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Predict probabilities on test set
    y_prob = model.predict_proba(X_test)[:, 1]

    # Evaluation metrics
    metrics = {
        "auc_roc": roc_auc_score(y_test, y_prob),
        "brier_score": brier_score_loss(y_test, y_prob),
        "log_loss": log_loss(y_test, y_prob),
    }

    logger.info(f"Model performance:")
    logger.info(f"  AUC-ROC:     {metrics['auc_roc']:.4f}")
    logger.info(f"  Brier Score: {metrics['brier_score']:.4f}")
    logger.info(f"  Log Loss:    {metrics['log_loss']:.4f}")

    return {
        "model": model,
        "X_test": X_test,
        "y_test": y_test,
        "y_prob": y_prob,
        "metrics": metrics,
        "feature_names": list(X.columns),
    }


def compute_cpoe(
    pass_plays: pd.DataFrame, model: xgb.XGBClassifier, feature_names: list[str]
) -> pd.DataFrame:
    """
    Compute Completion Percentage Over Expected (CPOE) for each QB.

    For every throw, the model predicts the expected completion probability.
    CPOE = actual completion rate - mean predicted completion rate.

    A positive CPOE means the QB completes passes at a higher rate than
    expected given the difficulty of their throws.
    """
    throws = pass_plays[
        (pass_plays["sack"] == 0)
        & (pass_plays["qb_scramble"] == 0)
        & (pass_plays["air_yards"].notna())
    ].copy()

    # One-hot encode pass location if needed
    if "pass_location" in throws.columns:
        location_dummies = pd.get_dummies(throws["pass_location"], prefix="pass_location")
        throws = pd.concat([throws, location_dummies], axis=1)

    # Get available features
    available_features = [f for f in feature_names if f in throws.columns]
    X_all = throws[available_features].fillna(throws[available_features].median())

    # Predict completion probability for every throw
    throws["xcomp"] = model.predict_proba(X_all)[:, 1]

    # Aggregate per QB
    cpoe_df = throws.groupby("passer_player_id").agg(
        player_name=("passer_player_name", "first"),
        team=("posteam", lambda x: x.mode().iloc[0]),
        attempts=("complete_pass", "count"),
        actual_comp_pct=("complete_pass", "mean"),
        expected_comp_pct=("xcomp", "mean"),
    )

    cpoe_df["cpoe"] = cpoe_df["actual_comp_pct"] - cpoe_df["expected_comp_pct"]

    # Sort by CPOE
    cpoe_df = cpoe_df.sort_values("cpoe", ascending=False)

    logger.info("CPOE Leaders:")
    for _, row in cpoe_df.head(5).iterrows():
        logger.info(
            f"  {row['player_name']}: {row['cpoe']:+.2%} "
            f"({row['actual_comp_pct']:.1%} actual vs {row['expected_comp_pct']:.1%} expected)"
        )

    return cpoe_df


def compute_shap_values(model: xgb.XGBClassifier, X_test: pd.DataFrame) -> shap.Explanation:
    """
    Compute SHAP values for model interpretability.

    Returns SHAP Explanation object for creating summary plots,
    waterfall charts, and feature importance analysis.
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_test)
    logger.info("SHAP values computed")
    return shap_values
