"""
pipeline/gold.py — Capa Gold: User 360°
Transforma eventos (nivel fila) → perfiles de usuario (nivel entidad).
Una fila en Gold = un usuario completo con su historia financiera resumida.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SILVER_FILE, GOLD_FILE,
    HIGH_VALUE_THRESHOLD, LOW_BALANCE_THRESHOLD, HIGH_FAIL_RATIO, DORMANT_TRANSACTIONS
)

# Categorías de gasto conocidas (excluye recarga)
SPEND_CATEGORIES = ["services", "shopping", "entertainment", "transport", "food"]


def run_gold(silver_df: pd.DataFrame = None) -> pd.DataFrame:
    """Construye el perfil User 360° desde Silver."""
    print("▶ Gold: construyendo User 360°...")

    df = silver_df.copy() if silver_df is not None else pd.read_parquet(SILVER_FILE)

    # Solo transacciones financieras reales para las métricas de gasto
    fin = df[df["is_financial"] == 1].copy()
    spend = fin[fin["event_type"] != "MONEY_ADDED"].copy()

    # ── 1. Demografía ─────────────────────────────────────────────────────
    demo = (
        df.sort_values("timestamp").groupby("userId")
        .agg(
            name            = ("name",    "last"),
            age             = ("age",     "last"),
            email           = ("email",   "last"),
            segment         = ("segment", "last"),
            city            = ("city",    "last"),
            country         = ("country", "last"),
        )
        .reset_index()
    )

    # ── 2. Volumen financiero ──────────────────────────────────────────────
    volume = (
        spend.groupby("userId")["amount"]
        .agg(
            total_spent       = "sum",
            avg_transaction   = "mean",
            median_transaction= "median",
            max_transaction   = "max",
        )
        .reset_index()
    )

    # ── 3. Actividad ───────────────────────────────────────────────────────
    activity = (
        fin.groupby("userId")
        .agg(
            n_transactions = ("event_id",  "count"),
            n_failed       = ("is_failed", "sum"),
            n_success      = ("is_success","sum"),
            unique_days_active = ("date",  "nunique"),
        )
        .reset_index()
    )
    activity["fail_ratio"] = (
        activity["n_failed"] / activity["n_transactions"].replace(0, np.nan)
    ).fillna(0)

    # ── 4. Balance ─────────────────────────────────────────────────────────
    balance = (
        fin.groupby("userId")
        .agg(
            current_balance  = ("balance_after",  "last"),
            min_balance      = ("balance_after",  "min"),
            max_balance      = ("balance_after",  "max"),
            avg_balance      = ("balance_after",  "mean"),
            balance_std      = ("balance_after",  "std"),
            total_added      = ("amount",         lambda x: x[fin.loc[x.index, "event_type"] == "MONEY_ADDED"].sum()),
            total_withdrawn  = ("balance_delta",  lambda x: x[x < 0].abs().sum()),
        )
        .reset_index()
    )
    balance["balance_std"] = balance["balance_std"].fillna(0)

    # ── 5. Categorías de gasto (pivot) ────────────────────────────────────
    cat_spend = spend[spend["category"].isin(SPEND_CATEGORIES)].copy()
    if not cat_spend.empty:
        cat_pivot = (
            cat_spend.groupby(["userId", "category"])["amount"]
            .sum()
            .unstack(fill_value=0)
            .reset_index()
        )
        # Asegurar que todas las columnas existen
        for cat in SPEND_CATEGORIES:
            col = f"cat_{cat}"
            if cat in cat_pivot.columns:
                cat_pivot.rename(columns={cat: col}, inplace=True)
            else:
                cat_pivot[col] = 0
        cat_cols = ["userId"] + [f"cat_{c}" for c in SPEND_CATEGORIES]
        cat_pivot = cat_pivot[[c for c in cat_cols if c in cat_pivot.columns]]
    else:
        cat_pivot = demo[["userId"]].copy()
        for cat in SPEND_CATEGORIES:
            cat_pivot[f"cat_{cat}"] = 0

    # ── 6. Temporales ──────────────────────────────────────────────────────
    temporal = (
        fin.groupby("userId")
        .agg(
            peak_hour              = ("hour",       lambda x: x.mode()[0] if len(x) > 0 else 0),
            weekend_transactions   = ("is_weekend", "sum"),
            preferred_channel      = ("channel",    lambda x: x.mode()[0] if len(x) > 0 else "unknown"),
            preferred_device       = ("device",     lambda x: x.mode()[0] if len(x) > 0 else "unknown"),
        )
        .reset_index()
    )

    # ── 7. Merge de todas las capas ────────────────────────────────────────
    gold = demo.copy()
    for other in [volume, activity, balance, cat_pivot, temporal]:
        gold = gold.merge(other, on="userId", how="left")

    # Rellenar NaN en columnas numéricas
    num_cols = gold.select_dtypes(include=[np.number]).columns
    gold[num_cols] = gold[num_cols].fillna(0)

    # ── 8. Flags de riesgo / valor ─────────────────────────────────────────
    gold["is_high_value"]    = (gold["total_spent"]  >= HIGH_VALUE_THRESHOLD).astype(int)
    gold["is_low_balance"]   = (gold["current_balance"] <= LOW_BALANCE_THRESHOLD).astype(int)
    gold["is_high_risk"]     = (gold["fail_ratio"]   >= HIGH_FAIL_RATIO).astype(int)
    gold["is_dormant"]       = (gold["n_transactions"] <= DORMANT_TRANSACTIONS).astype(int)
    gold["financial_stress"] = (
        (gold["is_low_balance"] == 1) & (gold["is_high_risk"] == 1)
    ).astype(int)

    GOLD_FILE.parent.mkdir(parents=True, exist_ok=True)
    gold.to_parquet(GOLD_FILE, index=False)
    print(f"  ✓ Gold: {len(gold):,} usuarios, {len(gold.columns)} features")
    return gold


if __name__ == "__main__":
    run_gold()
