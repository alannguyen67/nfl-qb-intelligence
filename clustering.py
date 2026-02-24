"""
Unsupervised clustering pipeline for QB play style analysis.

Uses UMAP for dimensionality reduction and HDBSCAN for density-based
clustering. Provides utilities for labeling and interpreting clusters.
"""

import logging
from dataclasses import dataclass

import hdbscan
import numpy as np
import pandas as pd
import umap

logger = logging.getLogger(__name__)


@dataclass
class ClusteringResult:
    """Container for clustering output."""

    labels: np.ndarray
    embedding_2d: np.ndarray
    cluster_profiles: pd.DataFrame
    cluster_names: dict[int, str]
    n_clusters: int


def fit_umap(X_scaled: pd.DataFrame, n_components: int = 2, random_state: int = 42) -> np.ndarray:
    """
    Reduce feature dimensions with UMAP for visualization and clustering.

    Args:
        X_scaled: Standardized feature matrix
        n_components: Target dimensions (2 for visualization)
        random_state: Seed for reproducibility

    Returns:
        2D embedding array
    """
    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=10,       # small dataset → smaller neighborhood
        min_dist=0.1,
        metric="euclidean",
        random_state=random_state,
    )
    embedding = reducer.fit_transform(X_scaled.values)
    logger.info(f"UMAP embedding shape: {embedding.shape}")
    return embedding


def fit_clusters(embedding: np.ndarray, min_cluster_size: int = 4) -> np.ndarray:
    """
    Cluster the UMAP embedding using HDBSCAN.

    HDBSCAN is density-based, so it:
    - Does not require predefining the number of clusters
    - Can label outliers as noise (-1)

    Args:
        embedding: 2D UMAP embedding
        min_cluster_size: Minimum points to form a cluster

    Returns:
        Array of cluster labels
    """
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=2,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(embedding)

    n_clusters = len(set(labels) - {-1})
    n_noise = (labels == -1).sum()
    logger.info(f"Found {n_clusters} clusters, {n_noise} noise points")
    return labels


def build_cluster_profiles(
    features: pd.DataFrame, labels: np.ndarray, feature_cols: list[str]
) -> pd.DataFrame:
    """
    Compute mean feature values per cluster to understand cluster identities.

    Returns:
        DataFrame with one row per cluster, showing mean of each feature.
    """
    df = features.copy()
    df["cluster"] = labels

    # Exclude noise points for profiling
    profiles = df[df["cluster"] != -1].groupby("cluster")[feature_cols].mean()
    return profiles


def auto_label_clusters(profiles: pd.DataFrame) -> dict[int, str]:
    """
    Heuristic labeling based on which features are highest/lowest per cluster.

    This is a starting point — you should manually review and refine labels.
    """
    labels = {}

    for cluster_id in profiles.index:
        row = profiles.loc[cluster_id]

        # Simple heuristic rules — expand as needed
        traits = []

        if row.get("avg_air_yards", 0) > profiles["avg_air_yards"].median():
            traits.append("Aggressive")
        else:
            traits.append("Conservative")

        if row.get("scramble_rate_mobility", 0) > profiles["scramble_rate_mobility"].median():
            traits.append("Mobile")
        else:
            traits.append("Pocket")

        if row.get("clutch_epa", 0) > profiles["clutch_epa"].median():
            traits.append("Clutch")

        if row.get("pressure_resilience", 0) > profiles["pressure_resilience"].median():
            traits.append("Composed")

        labels[cluster_id] = " / ".join(traits[:2])  # Keep it concise

    return labels


def run_clustering_pipeline(
    features: pd.DataFrame,
    X_scaled: pd.DataFrame,
    feature_cols: list[str],
) -> ClusteringResult:
    """
    Full clustering pipeline: UMAP → HDBSCAN → profile → label.

    Args:
        features: Original (unscaled) feature matrix with QB metadata
        X_scaled: Standardized feature matrix
        feature_cols: List of feature column names

    Returns:
        ClusteringResult with all outputs
    """
    logger.info("Running clustering pipeline...")

    # Step 1: Dimensionality reduction
    embedding = fit_umap(X_scaled)

    # Step 2: Cluster
    labels = fit_clusters(embedding)

    # Step 3: Profile clusters
    profiles = build_cluster_profiles(features, labels, feature_cols)

    # Step 4: Auto-label (starting point)
    cluster_names = auto_label_clusters(profiles)

    n_clusters = len(set(labels) - {-1})

    result = ClusteringResult(
        labels=labels,
        embedding_2d=embedding,
        cluster_profiles=profiles,
        cluster_names=cluster_names,
        n_clusters=n_clusters,
    )

    logger.info(f"Clustering complete. {n_clusters} clusters identified.")
    for cid, name in cluster_names.items():
        count = (labels == cid).sum()
        logger.info(f"  Cluster {cid} ({name}): {count} QBs")

    return result
