"""
models/anomaly.py — Versión optimizada
Isolation Forest para detección de anomalías a nivel de transacción
"""

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ISOLATION_FOREST_CONTAMINATION, RANDOM_STATE, SILVER_FILE


# ── Features mejoradas ─────────────────────────────────────────────
ANOMALY_FEATURES = [
    "amount",
    "balance_delta",
    "hour",
    "is_failed",
    "is_weekend",
]


def add_derived_features(df):
    """Features adicionales para mejorar detección"""
    df = df.copy()

    # Magnitud relativa del cambio
    df["relative_delta"] = df["balance_delta"] / df["balance_before"].replace(0, np.nan)

    # Intensidad de transacción
    df["amount_vs_balance"] = df["amount"] / df["balance_before"].replace(0, np.nan)

    return df.fillna(0)


def log_transform(X):
    """Transformación log para reducir skew en montos"""
    for col in ["amount", "balance_delta"]:
        if col in X.columns:
            X[col] = np.sign(X[col]) * np.log1p(np.abs(X[col]))
    return X


def remove_outliers(X):
    """Clipping de outliers extremos"""
    return X.clip(lower=X.quantile(0.01), upper=X.quantile(0.99), axis=1)


def run_anomaly_detection(silver_df: pd.DataFrame = None):
    """
    Detecta anomalías en transacciones.

    Returns:
        df: dataframe completo con flags
        n_anomalies: total anomalías
        top_anomalies: top 50 más raras
    """

    print("▶ Anomaly Detection optimizado...")

    df = silver_df.copy() if silver_df is not None else pd.read_parquet(SILVER_FILE)

    # ── Filtrar transacciones financieras ───────────────────────────
    fin = df[df["is_financial"] == 1].copy()

    # ── Features base ──────────────────────────────────────────────
    fin = add_derived_features(fin)

    features = ANOMALY_FEATURES + [
        "relative_delta",
        "amount_vs_balance",
    ]

    features = [f for f in features if f in fin.columns]

    X = fin[features].fillna(0)

    # ── Transformaciones ───────────────────────────────────────────
    X = log_transform(X)
    X = remove_outliers(X)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ── Modelo ─────────────────────────────────────────────────────
    iso = IsolationForest(
        contamination=ISOLATION_FOREST_CONTAMINATION,
        random_state=RANDOM_STATE,
        n_estimators=150,
    )

    fin["anomaly_pred"] = iso.fit_predict(X_scaled)   # -1 = anómalo
    fin["anomaly_score"] = iso.decision_function(X_scaled)

    # Score más intuitivo: mayor = más raro
    fin["anomaly_score"] = -fin["anomaly_score"]

    fin["is_anomaly"] = (fin["anomaly_pred"] == -1).astype(int)

    # ── Métricas ───────────────────────────────────────────────────
    n_anomalies = fin["is_anomaly"].sum()
    pct = n_anomalies / len(fin) * 100

    print(f"  ✓ Anomalías detectadas: {n_anomalies} / {len(fin)} ({pct:.2f}%)")

    

    # ── Top anomalías ──────────────────────────────────────────────
    top_anomalies = (
        fin[fin["is_anomaly"] == 1]
        .sort_values("anomaly_score", ascending=False)
        .head(50)[[
            "event_id", "userId", "event_type",
            "amount", "balance_delta",
            "relative_delta", "amount_vs_balance",
            "merchant", "category",
            "hour", "is_failed",
            "anomaly_score", "timestamp"
        ]]
    )

    # ── Merge al dataset completo ──────────────────────────────────
    anomaly_map = fin[["event_id", "is_anomaly", "anomaly_score"]].set_index("event_id")

    df = df.join(anomaly_map, on="event_id", how="left")

    df["is_anomaly"] = df["is_anomaly"].fillna(0).astype(int)
    df["anomaly_score"] = df["anomaly_score"].fillna(0)


    # ───────────────── VALIDACIÓN ─────────────────

    print("\n🔍 Comparación normal vs anomalía:")
    print(
        df.groupby("is_anomaly")[[
            "amount",
            "balance_delta",
            "is_failed"
        ]].mean().round(2)
    )

    import matplotlib.pyplot as plt

    print("\n📊 Generando histogramas...")

    plt.figure()
    df[df["is_anomaly"] == 0]["amount"].hist(bins=50)
    plt.title("Montos - Normales")

    plt.figure()
    df[df["is_anomaly"] == 1]["amount"].hist(bins=50)
    plt.title("Montos - Anomalías")

    plt.show()

    print("\n🚨 Top 10 anomalías:")
    print(
        df[df["is_anomaly"] == 1]
        .sort_values("anomaly_score", ascending=False)
        .head(10)[[
            "event_id",
            "userId",
            "amount",
            "balance_delta",
            "is_failed",
            "hour",
            "anomaly_score"
        ]]
    )

    print("\n👤 Usuarios con más anomalías:")
    print(
        df.groupby("userId")["is_anomaly"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
    )

    print("\n⚠️ Relación anomalías vs fallos:")
    print(
        df.groupby("is_anomaly")["is_failed"]
        .mean()
        .round(3)
    )

    plt.figure()
    df["anomaly_score"].hist(bins=50)
    plt.title("Distribución Anomaly Score")
    plt.show()

    # ── Guardar resultados ─────────────────────────────────────────
    Path("data/silver").mkdir(parents=True, exist_ok=True)

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str)

    df.to_parquet("data/silver/silver_with_anomalies.parquet", index=False)

    Path("models").mkdir(exist_ok=True)
    joblib.dump(iso, "models/isolation_forest.pkl")
    joblib.dump(scaler, "models/anomaly_scaler.pkl")

    print("  ✓ Modelo y resultados guardados")

    return df, n_anomalies, top_anomalies


if __name__ == "__main__":
    run_anomaly_detection()
