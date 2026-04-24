
"""
pipeline/silver.py — Capa Silver

Limpieza, normalización, enriquecimiento y features de negocio.
Lee Bronze, escribe Silver.
"""

import pandas as pd
from pathlib import Path
import sys
from enrichment.apis import enrich_events_dataframe
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import BRONZE_FILE, SILVER_FILE

FINANCIAL_EVENTS = {
    "PAYMENT_COMPLETED", "PAYMENT_FAILED",
    "TRANSFER_SENT", "TRANSFER_RECEIVED",
    "WITHDRAWAL", "MONEY_ADDED",
}

TIME_SLOTS = {
    range(0, 6):   "madrugada",
    range(6, 12):  "mañana",
    range(12, 18): "tarde",
    range(18, 24): "noche",
}


def get_time_slot(hour: int) -> str:
    for r, label in TIME_SLOTS.items():
        if hour in r:
            return label
    return "noche"


def run_silver(bronze_df: pd.DataFrame = None) -> pd.DataFrame:
    print("▶ Silver: limpieza, enriquecimiento y features...")

    df = bronze_df.copy() if bronze_df is not None else pd.read_parquet(BRONZE_FILE)

    # ── 1. Limpieza básica ───────────────────────────────────────────────
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").abs().fillna(0)
    df["balance_before"] = pd.to_numeric(df["balance_before"], errors="coerce").fillna(0)
    df["balance_after"] = pd.to_numeric(df["balance_after"], errors="coerce").fillna(0)

    # ── 2. Enriquecimiento ───────────────────────────────────────────────
    try:
        from enrichment.apis import enrich_events_dataframe
        print("  📡 Enriqueciendo con APIs open source...")
        df = enrich_events_dataframe(df, enable_geo=True, enable_fx=True)
    except Exception as e:
        print(f"  ⚠️ Enriquecimiento omitido: {e}")
        df["amount_cop"] = df["amount"]
        df["usd_cop_rate"] = 4150.0

    # ── 3. Timestamps ────────────────────────────────────────────────────
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["date"] = df["timestamp"].dt.date
    df["date"] = pd.to_datetime(df["timestamp"]).dt.normalize()
    df["time_slot"] = df["hour"].apply(get_time_slot)

    # ── 4. Features financieras ──────────────────────────────────────────
    df["balance_delta"] = df["balance_after"] - df["balance_before"]

    # ── 5. Flags de negocio ──────────────────────────────────────────────
    df["is_financial"] = df["event_type"].isin(FINANCIAL_EVENTS).astype(int)
    df["is_failed"] = (df["event_status"] == "FAILED").astype(int)
    df["is_success"] = (df["event_status"] == "SUCCESS").astype(int)

    # ── 6. Ubicación (corregido) ─────────────────────────────────────────
    df.rename(columns={
        "city_payload": "user_city",
        "city_location": "transaction_city"
    }, inplace=True)

    # ── 7. Categorías ────────────────────────────────────────────────────
    df["category"] = df["category"].fillna("recarga")
    df.loc[df["event_type"] == "MONEY_ADDED", "category"] = "recarga"

    # ── Guardado ─────────────────────────────────────────────────────────
    SILVER_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SILVER_FILE, index=False)

    print(f"  ✓ Silver: {len(df):,} filas, {df['userId'].nunique()} usuarios únicos")

    return df


if __name__ == "__main__":
    run_silver()