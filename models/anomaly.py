"""
models/anomaly.py — Isolation Forest: Detección de Anomalías
Opera a nivel de transacción (Silver), no de usuario.
Captura anomalías de monto, comportamiento y patrones de fallo.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ISOLATION_FOREST_CONTAMINATION, RANDOM_STATE, SILVER_FILE

# Features de anomalía: monto + balance + hora + fallo
ANOMALY_FEATURES = ["amount", "balance_delta", "hour", "is_failed"]


def run_anomaly_detection(silver_df: pd.DataFrame = None):
    """
    Detecta transacciones anómalas en Silver.
    Retorna (silver_df_con_anomalia, n_anomalias, top_anomalias).
    """
    print("▶ Anomaly Detection: Isolation Forest...")

    df = silver_df.copy() if silver_df is not None else pd.read_parquet(SILVER_FILE)

    # Solo transacciones financieras con datos completos
    fin = df[df["is_financial"] == 1].copy()
    features = [f for f in ANOMALY_FEATURES if f in fin.columns]
    X = fin[features].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(
        contamination=ISOLATION_FOREST_CONTAMINATION,
        random_state=RANDOM_STATE,
        n_estimators=100,
    )
    fin["anomaly_pred"]  = iso.fit_predict(X_scaled)   # -1=anomalía, 1=normal
    fin["anomaly_score"] = iso.decision_function(X_scaled)  # menor = más anómalo
    fin["is_anomaly"]    = (fin["anomaly_pred"] == -1).astype(int)

    n_anomalies = fin["is_anomaly"].sum()
    pct = n_anomalies / len(fin) * 100

    # Top anomalías para el dashboard
    top_anomalies = (
        fin[fin["is_anomaly"] == 1]
        .sort_values("anomaly_score")
        .head(50)[
            ["event_id", "userId", "event_type", "amount",
             "merchant", "category", "hour", "is_failed",
             "balance_delta", "anomaly_score", "timestamp"]
        ]
    )

    print(f"  ✓ Anomalías detectadas: {n_anomalies} / {len(fin)} ({pct:.1f}%)")

    # Merge anomaly flags de vuelta al df completo
    anomaly_map = fin[["event_id", "is_anomaly", "anomaly_score"]].set_index("event_id")
    df = df.join(anomaly_map, on="event_id", how="left")
    df["is_anomaly"]    = df["is_anomaly"].fillna(0).astype(int)
    df["anomaly_score"] = df["anomaly_score"].fillna(0)

    return df, n_anomalies, top_anomalies
