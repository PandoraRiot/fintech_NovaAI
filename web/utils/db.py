"""
utils/db.py — Capa de persistencia en PostgreSQL
Guarda el Gold layer y anomalías para consultas SQL directas.
Graceful degradation: si no hay DB, funciona en modo solo-Parquet.
"""
import os
import logging
import pandas as pd
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_engine = None


def get_engine():
    """Inicializa la conexión a PostgreSQL (lazy, singleton)."""
    global _engine
    if _engine is not None:
        return _engine

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return None

    try:
        from sqlalchemy import create_engine
        _engine = create_engine(db_url, pool_pre_ping=True, pool_size=5)
        # Test connection
        with _engine.connect() as conn:
            conn.execute(__import__('sqlalchemy').text("SELECT 1"))
        logger.info("✓ PostgreSQL conectado")
        return _engine
    except Exception as e:
        logger.warning(f"⚠️  PostgreSQL no disponible: {e} — modo Parquet")
        return None


def save_gold_to_db(gold_df: pd.DataFrame, run_meta: dict = None):
    """Persiste el Gold layer en PostgreSQL."""
    engine = get_engine()
    if engine is None:
        return False

    try:
        cols_to_save = [c for c in gold_df.columns if c not in ["segment_icon", "segment_color"]]
        gold_df[cols_to_save].to_sql(
            "user_360", engine,
            if_exists="replace", index=False, chunksize=500,
        )
        logger.info(f"✓ Gold layer guardado en DB: {len(gold_df)} usuarios")

        if run_meta:
            pd.DataFrame([{**run_meta, "run_at": datetime.now()}]).to_sql(
                "pipeline_runs", engine, if_exists="append", index=False
            )
        return True
    except Exception as e:
        logger.error(f"Error guardando en DB: {e}")
        return False


def save_anomalies_to_db(anomalies_df: pd.DataFrame):
    """Persiste anomalías detectadas en PostgreSQL."""
    engine = get_engine()
    if engine is None:
        return False

    try:
        cols = ["event_id", "userId", "event_type", "amount", "merchant", "category", "anomaly_score"]
        available = [c for c in cols if c in anomalies_df.columns]
        df = anomalies_df[available].rename(columns={"userId": "user_id"})
        df.to_sql("anomalies", engine, if_exists="replace", index=False, chunksize=200)
        logger.info(f"✓ {len(df)} anomalías guardadas en DB")
        return True
    except Exception as e:
        logger.error(f"Error guardando anomalías: {e}")
        return False


def query_user_from_db(user_id: str) -> Optional[pd.Series]:
    """Lee un usuario directamente de la DB (para queries dinámicas)."""
    engine = get_engine()
    if engine is None:
        return None

    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            df = pd.read_sql(
                text("SELECT * FROM user_360 WHERE user_id = :uid"),
                conn, params={"uid": user_id}
            )
        return df.iloc[0] if len(df) > 0 else None
    except Exception:
        return None
