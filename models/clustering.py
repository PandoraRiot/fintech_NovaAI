"""
models/clustering.py — KMeans Clustering: Segmentación de Usuarios
Produce 4 arquetipos financieros con etiquetado automático por centroide.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import KMEANS_K, RANDOM_STATE, GOLD_FILE

# Features que capturan el comportamiento financiero integral
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


def label_clusters(kmeans: KMeans, feature_names: list) -> dict:
    """
    Asigna etiquetas semánticas a clusters según su centroide.
    Ordena por score compuesto (total_spent + balance - fail_ratio)
    de mejor a peor perfil financiero y asigna etiquetas únicas.
    """
    centers = pd.DataFrame(kmeans.cluster_centers_, columns=feature_names)

    # Score compuesto: mayor gasto + mayor balance - mayor fallo = mejor perfil
    if "total_spent" in centers.columns and "current_balance" in centers.columns:
        centers["_score"] = (
            centers["total_spent"].rank()
            + centers["current_balance"].rank()
            - centers["fail_ratio"].rank() * 2
        )
    else:
        centers["_score"] = range(len(centers))

    rank_order = centers["_score"].rank(ascending=False).astype(int) - 1
    # rank 0 = premium, 1 = activo, 2 = dormido, 3 = riesgo
    LABEL_MAP = {
        0: ("👑", "Premium Activo",      "#7C3AED"),
        1: ("📈", "Activo Estándar",     "#2563EB"),
        2: ("😴", "Dormido / Ocasional", "#6B7280"),
        3: ("⚠️", "En Riesgo",          "#DC2626"),
    }
    cluster_labels = {}
    for cluster_id, label_rank in rank_order.items():
        cluster_labels[cluster_id] = LABEL_MAP[label_rank]
    return cluster_labels


def run_clustering(gold_df: pd.DataFrame = None):
    """
    Entrena KMeans sobre el perfil Gold y añade columnas de cluster.
    Retorna (gold_df_con_cluster, kmeans, scaler, silhouette).
    """
    print("▶ Clustering: KMeans k=4...")

    gold = gold_df.copy() if gold_df is not None else pd.read_parquet(GOLD_FILE)

    # Seleccionar solo features disponibles
    features = [f for f in CLUSTER_FEATURES if f in gold.columns]
    X = gold[features].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=KMEANS_K, random_state=RANDOM_STATE, n_init=10)
    gold["cluster"] = kmeans.fit_predict(X_scaled)

    sil = silhouette_score(X_scaled, gold["cluster"])

    # Etiquetado dinámico por centroide
    cluster_labels = label_clusters(kmeans, features)
    gold["segment_icon"]  = gold["cluster"].map(lambda c: cluster_labels[c][0])
    gold["segment_name"]  = gold["cluster"].map(lambda c: cluster_labels[c][1])
    gold["segment_color"] = gold["cluster"].map(lambda c: cluster_labels[c][2])

    print(f"  ✓ Silhouette score: {sil:.3f}")
    for c, (icon, name, _) in cluster_labels.items():
        n = (gold["cluster"] == c).sum()
        print(f"    {icon} {name}: {n} usuarios ({n/len(gold)*100:.1f}%)")

    return gold, kmeans, scaler, sil, cluster_labels
