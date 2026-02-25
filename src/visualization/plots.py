"""
Visualization functions for the QB Intelligence project.

Provides reusable, publication-quality plots for:
- Cluster scatter plots (UMAP embedding)
- Radar charts for QB comparison
- CPOE leaderboards
- SHAP summary plots
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ──────────────────────────────────────────────────────────────────────
# Color palette
# ──────────────────────────────────────────────────────────────────────
CLUSTER_COLORS = px.colors.qualitative.Set2
ACCENT_COLOR = "#1f77b4"


# ──────────────────────────────────────────────────────────────────────
# Cluster visualization
# ──────────────────────────────────────────────────────────────────────


def plot_cluster_map(
    features: pd.DataFrame,
    embedding: np.ndarray,
    labels: np.ndarray,
    cluster_names: dict[int, str],
    title: str = "QB Play Style Clusters (UMAP + HDBSCAN)",
) -> go.Figure:
    """
    Interactive scatter plot of QB clusters in UMAP space.

    Each point is a QB, colored by cluster, with hover info showing
    key stats.
    """
    plot_df = features[["player_name", "team", "pass_attempts"]].copy()
    plot_df["umap_1"] = embedding[:, 0]
    plot_df["umap_2"] = embedding[:, 1]
    plot_df["cluster"] = labels
    plot_df["cluster_name"] = plot_df["cluster"].map(
        lambda c: cluster_names.get(c, "Unclustered")
    )

    fig = px.scatter(
        plot_df,
        x="umap_1",
        y="umap_2",
        color="cluster_name",
        hover_data=["player_name", "team", "pass_attempts"],
        text="player_name",
        title=title,
        color_discrete_sequence=CLUSTER_COLORS,
    )

    fig.update_traces(
        textposition="top center",
        textfont_size=9,
        marker=dict(size=12, line=dict(width=1, color="white")),
    )
    fig.update_layout(
        plot_bgcolor="white",
        width=900,
        height=650,
        xaxis_title="UMAP Dimension 1",
        yaxis_title="UMAP Dimension 2",
        legend_title="Play Style",
    )
    return fig


# ──────────────────────────────────────────────────────────────────────
# Radar chart for QB comparison
# ──────────────────────────────────────────────────────────────────────


def plot_radar_comparison(
    features: pd.DataFrame,
    qb_ids: list[str],
    metrics: list[str] = None,
    metric_labels: dict[str, str] = None,
) -> go.Figure:
    """
    Radar chart comparing 2-4 QBs across key metrics.

    Features are min-max scaled to [0, 1] for visual comparability.
    """
    if metrics is None:
        metrics = [
            "avg_air_yards",
            "deep_ball_rate",
            "overall_comp_pct",
            "pressure_resilience",
            "clutch_epa",
            "scramble_rate_mobility",
        ]

    if metric_labels is None:
        metric_labels = {
            "avg_air_yards": "Air Yards",
            "deep_ball_rate": "Deep Ball %",
            "overall_comp_pct": "Completion %",
            "pressure_resilience": "Pressure Resilience",
            "clutch_epa": "Clutch EPA",
            "scramble_rate_mobility": "Mobility",
        }

    available_metrics = [m for m in metrics if m in features.columns]
    subset = features.loc[qb_ids, available_metrics].copy()

    # Min-max scale to [0, 1]
    for col in available_metrics:
        col_min = features[col].min()
        col_max = features[col].max()
        if col_max - col_min > 0:
            subset[col] = (subset[col] - col_min) / (col_max - col_min)
        else:
            subset[col] = 0.5

    labels = [metric_labels.get(m, m) for m in available_metrics]

    fig = go.Figure()

    for qb_id in qb_ids:
        name = features.loc[qb_id, "player_name"]
        values = subset.loc[qb_id].tolist()
        values.append(values[0])  # Close the polygon

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=labels + [labels[0]],
            fill="toself",
            name=name,
            opacity=0.6,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="QB Comparison — Radar Chart",
        width=700,
        height=600,
    )
    return fig


# ──────────────────────────────────────────────────────────────────────
# CPOE leaderboard
# ──────────────────────────────────────────────────────────────────────


def plot_cpoe_leaderboard(cpoe_df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """
    Horizontal bar chart showing CPOE leaders and laggards.
    """
    df = cpoe_df.head(top_n).copy() if top_n else cpoe_df.copy()
    df = df.sort_values("cpoe", ascending=True)  # ascending for horizontal bar

    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in df["cpoe"]]

    fig = go.Figure(go.Bar(
        x=df["cpoe"],
        y=df["player_name"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.1%}" for v in df["cpoe"]],
        textposition="outside",
    ))

    fig.update_layout(
        title="Completion % Over Expected (CPOE) — 2025 Season",
        xaxis_title="CPOE",
        yaxis_title="",
        plot_bgcolor="white",
        width=800,
        height=max(400, top_n * 30),
        xaxis=dict(tickformat=".0%", zeroline=True, zerolinecolor="black", zerolinewidth=1),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────
# Feature importance
# ──────────────────────────────────────────────────────────────────────


def plot_feature_importance(model, feature_names: list[str]) -> go.Figure:
    """Bar chart of XGBoost feature importances."""
    importance = model.feature_importances_
    sorted_idx = np.argsort(importance)

    fig = go.Figure(go.Bar(
        x=importance[sorted_idx],
        y=[feature_names[i] for i in sorted_idx],
        orientation="h",
        marker_color=ACCENT_COLOR,
    ))

    fig.update_layout(
        title="Completion Model — Feature Importance",
        xaxis_title="Importance (Gain)",
        plot_bgcolor="white",
        width=700,
        height=400,
    )
    return fig
