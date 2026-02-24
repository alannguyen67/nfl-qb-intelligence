# 🏈 NFL QB Intelligence — Play Style Clustering & Decision Analysis

A data science and ML project analyzing 2025-2026 NFL season quarterback performance through unsupervised clustering, custom performance metrics, and a completion probability model.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-In%20Development-yellow)

<!-- TODO: Add dashboard screenshot here -->
<!-- ![Dashboard Preview](reports/figures/dashboard_preview.png) -->

---

## Overview

Not all quarterbacks play the same game. This project uses play-by-play data from the 2025-2026 NFL season to:

1. **Engineer custom QB metrics** — Aggression Index, Pressure Resilience, Clutch Factor, and more
2. **Cluster QBs by play style** — using UMAP dimensionality reduction and HDBSCAN clustering to discover natural groupings like "Gunslingers," "Game Managers," and "Dual Threats"
3. **Model completion probability** — an XGBoost model predicting pass completion based on situational features, then measuring which QBs outperform expectations (CPOE)
4. **Visualize insights** — interactive Streamlit dashboard with radar charts, cluster maps, and KPI cards

## Key Metrics & KPIs

| Metric | Description |
|---|---|
| **Aggression Index** | Average air yards per attempt, deep ball rate (20+ air yards) |
| **Pressure Resilience** | EPA differential: under pressure vs. clean pocket |
| **Decisiveness Score** | Derived from time-to-throw distribution and sack rate |
| **Clutch Factor** | EPA in high-leverage situations (4th quarter, close games) |
| **Mobility Score** | Scramble rate, rushing yards on designed pass plays |
| **CPOE** | Completion Percentage Over Expected — model-derived |

## Project Structure

```
nfl-qb-intelligence/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .gitignore
│
├── data/
│   ├── raw/                  # Raw play-by-play and roster data
│   └── processed/            # Cleaned, feature-engineered datasets
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_clustering_analysis.ipynb
│   └── 04_completion_probability_model.ipynb
│
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   └── load_data.py      # Data acquisition & cleaning pipeline
│   ├── features/
│   │   ├── __init__.py
│   │   └── build_features.py # Feature engineering for QB metrics
│   ├── models/
│   │   ├── __init__.py
│   │   ├── clustering.py     # UMAP + HDBSCAN clustering pipeline
│   │   └── completion_model.py  # XGBoost completion probability
│   └── visualization/
│       ├── __init__.py
│       └── plots.py          # Reusable plotting functions
│
├── app/
│   └── dashboard.py          # Streamlit dashboard
│
├── tests/
│   ├── __init__.py
│   ├── test_features.py
│   └── test_models.py
│
└── reports/
    └── figures/              # Saved plots and dashboard screenshots
```

## Setup & Installation

### Prerequisites
- Python 3.11+
- macOS / Linux / WSL

### Quick Start

```bash
# Clone the repo
git clone https://github.com/alannguyen67/nfl-qb-intelligence.git
cd nfl-qb-intelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Pull the data
python -m src.data.load_data

# Run the dashboard
streamlit run app/dashboard.py
```

## Methodology

### Data Source
Play-by-play data sourced via [`nfl_data_py`](https://github.com/cooperdff/nfl_data_py), which wraps the [nflverse](https://github.com/nflverse) data ecosystem — the gold standard for open NFL analytics data.

### Clustering Approach
1. Aggregate per-QB features from play-level data
2. Standardize features (StandardScaler)
3. Reduce dimensionality with UMAP (2 components for visualization)
4. Cluster with HDBSCAN (density-based, no need to predefine k)
5. Label clusters based on centroid feature profiles

### Completion Probability Model
- **Target:** Binary (complete / incomplete) on individual pass attempts
- **Features:** Air yards, pass location, pressure, down & distance, score differential, quarter, shotgun/no-huddle
- **Model:** XGBoost with hyperparameter tuning via Optuna
- **Evaluation:** AUC-ROC, Brier score, calibration curves
- **Interpretability:** SHAP values for global and per-prediction explanations

## Results

<!-- TODO: Fill in after analysis -->
*Coming soon — analysis in progress.*

## Tech Stack

- **Data:** pandas, nfl_data_py, numpy
- **ML:** scikit-learn, XGBoost, UMAP, HDBSCAN, Optuna
- **Interpretability:** SHAP
- **Visualization:** plotly, seaborn, matplotlib
- **Dashboard:** Streamlit
- **Dev:** pytest, ruff, GitHub Actions

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

- [nflverse](https://github.com/nflverse) for the incredible open data ecosystem
- [nfl_data_py](https://github.com/cooperdff/nfl_data_py) for the Python interface
- Ben Baldwin's [nflfastR](https://www.nflfastr.com/) for EPA methodology
