"""
NFL QB Intelligence Dashboard — Streamlit App

Interactive dashboard for exploring QB play style clusters,
comparing quarterbacks, and viewing completion probability insights.

Run with:
    streamlit run app/dashboard.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.features.build_features import build_qb_features, get_clustering_features
from src.models.clustering import run_clustering_pipeline
from src.models.completion_model import (
    compute_cpoe,
    compute_shap_values,
    prepare_model_data,
    train_completion_model,
)
from src.visualization.plots import (
    plot_cluster_map,
    plot_cpoe_leaderboard,
    plot_feature_importance,
    plot_radar_comparison,
)

# ──────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="NFL QB Intelligence",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏈 NFL QB Intelligence")
st.markdown("*Play style clustering & completion probability analysis — 2024-2026 seasons*")
st.divider()


# ──────────────────────────────────────────────────────────────────────
# Data loading (cached)
# ──────────────────────────────────────────────────────────────────────


@st.cache_data(show_spinner="Loading play-by-play data...")
def load_data():
    data_path = PROJECT_ROOT / "data" / "processed" / "pass_plays_qualified.parquet"
    if not data_path.exists():
        st.error(
            "Processed data not found. Run `python -m src.data.load_data` first."
        )
        st.stop()
    return pd.read_parquet(data_path)


@st.cache_data(show_spinner="Loading QB rush plays...")
def load_rush_data():
    rush_path = PROJECT_ROOT / "data" / "processed" / "qb_rush_plays_qualified.parquet"
    if not rush_path.exists():
        return None
    return pd.read_parquet(rush_path)


@st.cache_data(show_spinner="Engineering QB features...")
def get_features(_pass_plays, _rush_plays):
    return build_qb_features(_pass_plays, _rush_plays)


@st.cache_data(show_spinner="Running clustering pipeline...")
def get_clusters(_features, _X_scaled, _feature_cols):
    return run_clustering_pipeline(_features, _X_scaled, _feature_cols)


@st.cache_data(show_spinner="Training completion model...")
def get_model(_pass_plays):
    X, y = prepare_model_data(_pass_plays)
    result = train_completion_model(X, y)
    return result, X


# ──────────────────────────────────────────────────────────────────────
# Load everything
# ──────────────────────────────────────────────────────────────────────

pass_plays = load_data()
rush_plays = load_rush_data()
features = get_features(pass_plays, rush_plays)
X_scaled, feature_cols = get_clustering_features(features)
clustering_result = get_clusters(features, X_scaled, feature_cols)
model_result, model_X = get_model(pass_plays)

# Add cluster labels to features for display
features["cluster"] = clustering_result.labels
features["cluster_name"] = features["cluster"].map(
    lambda c: clustering_result.cluster_names.get(c, "Unclustered")
)


# ──────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────

st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["🏆 QB Rankings", "📊 Overview", "🗺️ Cluster Map", "🆚 QB Compare", "🎯 CPOE Analysis", "🤖 Model Details"],
)


# ──────────────────────────────────────────────────────────────────────
# Pages
# ──────────────────────────────────────────────────────────────────────

if page == "🏆 QB Rankings":
    st.subheader("QB Composite Rankings")
    st.markdown(
        "Weighted percentile-rank score across passing EPA, rushing EPA, clutch performance, "
        "pressure resilience, accuracy, sack avoidance, and deep-ball efficiency."
    )

    # Build rankings table
    ranking_cols = [
        "player_name", "team", "games_played", "composite_rating",
        "avg_intended_epa", "rushing_epa_per_game", "clutch_epa",
        "overall_comp_pct", "sack_rate", "dynamic_runner", "cluster_name",
    ]
    available_ranking = [c for c in ranking_cols if c in features.columns]
    rankings = features[available_ranking].copy().sort_values("composite_rating", ascending=False)
    rankings.insert(0, "Rank", range(1, len(rankings) + 1))

    # Format the dynamic runner badge as text
    if "dynamic_runner" in rankings.columns:
        rankings["dynamic_runner"] = rankings["dynamic_runner"].map(
            {True: "⚡ Dynamic Runner", False: ""}
        )

    st.dataframe(
        rankings.style.format({
            "composite_rating": "{:.1f}",
            "avg_intended_epa": "{:+.3f}",
            "rushing_epa_per_game": "{:+.3f}",
            "clutch_epa": "{:+.3f}",
            "overall_comp_pct": "{:.1%}",
            "sack_rate": "{:.1%}",
        }, na_rep="—"),
        use_container_width=True,
        hide_index=True,
    )

    # Highlight dual-threat QBs
    dynamic_runners = features[features["dynamic_runner"] == True]["player_name"].tolist()
    if dynamic_runners:
        st.caption(f"⚡ Dynamic Runners (85th+ percentile rushing EPA): {', '.join(dynamic_runners)}")

    # Weight legend
    with st.expander("Rating weights"):
        st.markdown("""
| Metric | Weight | Direction |
|---|---|---|
| Passing EPA/play | 25% | Higher = better |
| Rushing EPA/game | 12% | Higher = better |
| Clutch EPA | 18% | Higher = better |
| Pressure resilience | 15% | Higher = better |
| Completion % | 10% | Higher = better |
| Sack rate | 10% | **Lower = better** |
| Deep ball comp % | 10% | Higher = better |
        """)


elif page == "📊 Overview":
    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Qualifying QBs", len(features))
    col2.metric("Play Style Clusters", clustering_result.n_clusters)
    col3.metric("Total Pass Plays", f"{len(pass_plays):,}")
    col4.metric("Model AUC-ROC", f"{model_result['metrics']['auc_roc']:.3f}")

    st.subheader("QB Feature Summary")
    display_cols = [
        "player_name", "team", "pass_attempts", "games_played", "avg_air_yards",
        "deep_ball_rate", "overall_comp_pct", "rushing_epa_per_game", "clutch_epa", "cluster_name",
    ]
    available_display = [c for c in display_cols if c in features.columns]
    st.dataframe(
        features[available_display].sort_values("pass_attempts", ascending=False),
        use_container_width=True,
        hide_index=True,
    )


elif page == "🗺️ Cluster Map":
    st.subheader("QB Play Style Clusters")
    st.markdown(
        "Each point represents a quarterback, positioned by UMAP dimensionality "
        "reduction and colored by HDBSCAN cluster assignment."
    )

    fig = plot_cluster_map(
        features,
        clustering_result.embedding_2d,
        clustering_result.labels,
        clustering_result.cluster_names,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Cluster Profiles")
    st.dataframe(
        clustering_result.cluster_profiles.round(3),
        use_container_width=True,
    )


elif page == "🆚 QB Compare":
    st.subheader("Head-to-Head QB Comparison")

    qb_options = features["player_name"].sort_values().tolist()
    qb_id_map = features.reset_index().set_index("player_name")["passer_player_id"].to_dict()

    col1, col2 = st.columns(2)
    qb1_name = col1.selectbox("QB 1", qb_options, index=0)
    qb2_name = col2.selectbox("QB 2", qb_options, index=min(1, len(qb_options) - 1))

    qb1_id = qb_id_map.get(qb1_name)
    qb2_id = qb_id_map.get(qb2_name)

    if qb1_id and qb2_id:
        fig = plot_radar_comparison(features, [qb1_id, qb2_id])
        st.plotly_chart(fig, use_container_width=True)

        # Side-by-side stats
        st.subheader("Key Stats")
        compare_cols = [
            "pass_attempts", "avg_air_yards", "deep_ball_rate",
            "overall_comp_pct", "clutch_epa", "sack_rate",
        ]
        available_compare = [c for c in compare_cols if c in features.columns]
        compare_df = features.loc[[qb1_id, qb2_id], ["player_name"] + available_compare]
        st.dataframe(compare_df.set_index("player_name").T, use_container_width=True)


elif page == "🎯 CPOE Analysis":
    st.subheader("Completion % Over Expected (CPOE)")
    st.markdown(
        "CPOE measures how often a QB completes passes compared to what the model "
        "predicts given the difficulty of each throw."
    )

    cpoe_df = compute_cpoe(pass_plays, model_result["model"], model_result["feature_names"])

    fig = plot_cpoe_leaderboard(cpoe_df)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Full CPOE Table")
    st.dataframe(
        cpoe_df[["player_name", "team", "attempts", "actual_comp_pct", "expected_comp_pct", "cpoe"]]
        .style.format({
            "actual_comp_pct": "{:.1%}",
            "expected_comp_pct": "{:.1%}",
            "cpoe": "{:+.2%}",
        }),
        use_container_width=True,
        hide_index=True,
    )


elif page == "🤖 Model Details":
    st.subheader("Completion Probability Model")

    col1, col2, col3 = st.columns(3)
    col1.metric("AUC-ROC", f"{model_result['metrics']['auc_roc']:.4f}")
    col2.metric("Brier Score", f"{model_result['metrics']['brier_score']:.4f}")
    col3.metric("Log Loss", f"{model_result['metrics']['log_loss']:.4f}")

    st.subheader("Feature Importance")
    fig = plot_feature_importance(model_result["model"], model_result["feature_names"])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("SHAP Summary")
    st.markdown("*SHAP values show how each feature contributes to individual predictions.*")

    # SHAP computation
    with st.spinner("Computing SHAP values..."):
        import shap
        import matplotlib.pyplot as plt

        shap_values = compute_shap_values(model_result["model"], model_result["X_test"].head(500))

        fig_shap, ax = plt.subplots(figsize=(10, 6))
        shap.summary_plot(shap_values, model_result["X_test"].head(500), show=False)
        st.pyplot(fig_shap)
