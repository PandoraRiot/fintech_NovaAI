"""
models/clustering.py — Versión mejorada (estable)
"""

import numpy as np
import pandas as pd
import joblib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import KMEANS_K, RANDOM_STATE, GOLD_FILE


CLUSTER_FEATURES = [
    "total_spent",
    "avg_transaction",
    "n_transactions",
    "fail_ratio",
    "current_balance",
    "avg_balance",
    "unique_days_active",
    "cat_shopping",
    "cat_food",
    "cat_entertainment",
]


def add_derived_features(df):
    df = df.copy()

    # ── Features originales ─────────────────────────
    df["spend_per_txn"] = df["total_spent"] / df["n_transactions"].replace(0, np.nan)
    df["balance_per_txn"] = df["current_balance"] / df["n_transactions"].replace(0, np.nan)
    df["activity_ratio"] = df["n_transactions"] / df["unique_days_active"].replace(0, np.nan)

    # SE ELIMINA spend_vs_balance (muy inestable)

    # ── FIX ratios categorías (MUY IMPORTANTE) ──────
    for col in ["cat_shopping", "cat_food", "cat_entertainment"]:
        if col in df.columns:
            df[f"{col}_ratio"] = np.where(
                df["total_spent"] > 0,
                df[col] / df["total_spent"],
                0
            )

    # ── NUEVA FEATURE (aporta bastante) ─────────────
    df["transaction_frequency"] = df["n_transactions"] / df["unique_days_active"].replace(0, np.nan)

    return df.fillna(0)


def remove_outliers(X):
    return X.clip(lower=X.quantile(0.01), upper=X.quantile(0.99), axis=1)


def label_clusters(kmeans, scaler, features):

    centers_scaled = kmeans.cluster_centers_
    centers = pd.DataFrame(
        scaler.inverse_transform(centers_scaled),
        columns=features
    )

    centers["_score"] = (
    centers["total_spent"].rank(pct=True) * 0.4 +
    centers["current_balance"].rank(pct=True) * 0.3 -
    centers["fail_ratio"].rank(pct=True) * 0.3
    )

    centers = centers.sort_values("_score", ascending=False).reset_index()

    LABELS = [
        ("👑", "Premium Activo", "#7C3AED"),
        ("📈", "Activo Estándar", "#2563EB"),
        ("😴", "Dormido / Ocasional", "#6B7280"),
        ("⚠️", "En Riesgo", "#DC2626"),
    ]

    mapping = {}
    for i, row in centers.iterrows():
        mapping[row["index"]] = LABELS[i]

    return mapping, centers


def run_clustering(gold_df=None):
    print("▶ Clustering mejorado (estable)...")

    gold = gold_df.copy() if gold_df is not None else pd.read_parquet(GOLD_FILE)

    # ── Feature engineering ─────────────────────────
    gold = add_derived_features(gold)

    # ── Selección ───────────────────────────────────
    features = [f for f in CLUSTER_FEATURES if f in gold.columns]

    features += [
        "spend_per_txn",
        "balance_per_txn",
        "activity_ratio",
        "transaction_frequency",  # ← nueva buena
        "cat_shopping_ratio",
        "cat_food_ratio",
        "cat_entertainment_ratio",
    ]

    features = [f for f in features if f in gold.columns]

    X = gold[features].fillna(0)

    # ── Outliers ────────────────────────────────────
    X = remove_outliers(X)

    #----Tranformacion logaritmica-----
    X["total_spent"] = np.log1p(X["total_spent"])
    X["current_balance"] = np.log1p(X["current_balance"])

    # ── Escalado ────────────────────────────────────
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ── Modelo ──────────────────────────────────────
    kmeans = KMeans(
        n_clusters=KMEANS_K,
        random_state=RANDOM_STATE,
        n_init=20
    )

    gold["cluster"] = kmeans.fit_predict(X_scaled)

    # ── Métrica ─────────────────────────────────────
    sil = silhouette_score(X_scaled, gold["cluster"])

    # ── Etiquetas ───────────────────────────────────
    cluster_labels, centers = label_clusters(kmeans, scaler, features)

    gold["segment_icon"]  = gold["cluster"].map(lambda c: cluster_labels[c][0])
    gold["segment_name"]  = gold["cluster"].map(lambda c: cluster_labels[c][1])
    gold["segment_color"] = gold["cluster"].map(lambda c: cluster_labels[c][2])

    # ── Guardar ─────────────────────────────────────
    Path("data/gold").mkdir(parents=True, exist_ok=True)

    for col in gold.columns:
        if gold[col].dtype == "object":
            gold[col] = gold[col].astype(str)

    gold.to_parquet("data/gold/gold_clustered.parquet", index=False)

    Path("models").mkdir(exist_ok=True)
    joblib.dump(kmeans, "models/kmeans.pkl")
    joblib.dump(scaler, "models/scaler.pkl")

    # ── Debug ───────────────────────────────────────
    print(f"\n✓ Silhouette score: {sil:.3f}\n")

    print("📊 Distribución de clusters:")
    for c, (icon, name, _) in cluster_labels.items():
        n = (gold["cluster"] == c).sum()
        print(f"{icon} {name}: {n} usuarios ({n/len(gold)*100:.1f}%)")

    print("\n🧠 Centroides:")
    #print(centers.round(2))
    print(centers.sort_values("_score", ascending=False).round(2))
    return gold, kmeans, scaler, sil, cluster_labels


if __name__ == "__main__":
    run_clustering()