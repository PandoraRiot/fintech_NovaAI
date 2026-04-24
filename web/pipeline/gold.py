
"""
pipeline/gold.py — Capa Gold: User 360°
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

SPEND_CATEGORIES = ["services", "shopping", "entertainment", "transport", "food"]


def run_gold(silver_df: pd.DataFrame = None) -> pd.DataFrame:
    print("▶ Gold: construyendo User 360°...")

    df = silver_df.copy() if silver_df is not None else pd.read_parquet(SILVER_FILE)
    #transacciones financieras reales para las metricas
    fin = df[df["is_financial"] == 1].copy()
    spend = fin[fin["event_type"] != "MONEY_ADDED"].copy()

    # ── 1. Demografía ─────────────────────────────────
    demo = (
        df.sort_values("timestamp")
        .groupby("userId")
        .agg(
            name=("name", "last"),
            age=("age", "last"),
            email=("email", "last"),
            segment=("segment", "last"),
            user_city=("user_city", "last"),
            country=("country", "last"),
        )
        .reset_index()
    )

    # ── 2. Volumen financiero (usar COP) ──────────────
    volume = (
        spend.groupby("userId")["amount_cop"]
        .agg(
            total_spent="sum",
            avg_transaction="mean",
            median_transaction="median",
            max_transaction="max",
        )
        .reset_index()
    )

    # ── 3. Actividad ──────────────────────────────────
    activity = (
        fin.groupby("userId")
        .agg(
            n_transactions=("event_id", "count"),
            n_failed=("is_failed", "sum"),
            n_success=("is_success", "sum"),
            unique_days_active=("date", "nunique"),
        )
        .reset_index()
    )

    activity["fail_ratio"] = (
        activity["n_failed"] / activity["n_transactions"].replace(0, np.nan)
    ).fillna(0)

    # ── 4. Balance ────────────────────────────────────
    added = fin[fin["event_type"] == "MONEY_ADDED"].groupby("userId")["amount_cop"].sum().reset_index(name="total_added")

    withdrawn = fin[fin["balance_delta"] < 0].copy()
    withdrawn["withdraw"] = withdrawn["balance_delta"].abs()
    withdrawn = withdrawn.groupby("userId")["withdraw"].sum().reset_index(name="total_withdrawn")

    balance = (
        fin.groupby("userId")
        .agg(
            current_balance=("balance_after", "last"),
            min_balance=("balance_after", "min"),
            max_balance=("balance_after", "max"),
            avg_balance=("balance_after", "mean"),
            balance_std=("balance_after", "std"),
        )
        .reset_index()
    )

    balance = balance.merge(added, on="userId", how="left")
    balance = balance.merge(withdrawn, on="userId", how="left")

    balance["balance_std"] = balance["balance_std"].fillna(0)

    # ── 5. Categorías ─────────────────────────────────
    cat_spend = spend[spend["category"].isin(SPEND_CATEGORIES)]

    if not cat_spend.empty:
        cat_pivot = (
            cat_spend.groupby(["userId", "category"])["amount_cop"]
            .sum()
            .unstack(fill_value=0)
            .reset_index()
        )
        cat_pivot.columns = ["userId"] + [f"cat_{c}" for c in cat_pivot.columns if c != "userId"]

        # 🔥 ASEGURAR TODAS LAS CATEGORÍAS
        for cat in SPEND_CATEGORIES:
            col = f"cat_{cat}"
            if col not in cat_pivot.columns:
                cat_pivot[col] = 0

        # Ordenar columnas (opcional pero limpio)
        cat_pivot = cat_pivot[["userId"] + [f"cat_{c}" for c in SPEND_CATEGORIES]]

    else:
        cat_pivot = demo[["userId"]].copy()
        for c in SPEND_CATEGORIES:
            cat_pivot[f"cat_{c}"] = 0

    # ── 6. Temporal ───────────────────────────────────
    temporal = (
        fin.groupby("userId")
        .agg(
            peak_hour=("hour", lambda x: x.mode().iloc[0] if not x.mode().empty else 0),
            weekend_transactions=("is_weekend", "sum"),
            preferred_channel=("channel", lambda x: x.mode().iloc[0] if not x.mode().empty else "unknown"),
            preferred_device=("device", lambda x: x.mode().iloc[0] if not x.mode().empty else "unknown"),
        )
        .reset_index()
    )

    # ── 7. Merge ──────────────────────────────────────
    gold = demo.copy()
    for other in [volume, activity, balance, cat_pivot, temporal]:
        gold = gold.merge(other, on="userId", how="left")

    # ── 8. Features nuevas ────────────────────────────
    gold["spending_frequency"] = gold["n_transactions"] / gold["unique_days_active"].replace(0, np.nan)
    gold["spend_vs_add_ratio"] = gold["total_spent"] / gold["total_added"].replace(0, np.nan)

    # ── 9. Fill NA ────────────────────────────────────
    num_cols = gold.select_dtypes(include=[np.number]).columns
    gold[num_cols] = gold[num_cols].fillna(0)

    # ── 10. Flags ─────────────────────────────────────
    gold["is_high_value"] = (gold["total_spent"] >= HIGH_VALUE_THRESHOLD).astype(int)
    gold["is_low_balance"] = (gold["current_balance"] <= LOW_BALANCE_THRESHOLD).astype(int)
    gold["is_high_risk"] = (gold["fail_ratio"] >= HIGH_FAIL_RATIO).astype(int)
    gold["is_dormant"] = (gold["n_transactions"] <= DORMANT_TRANSACTIONS).astype(int)

    gold["financial_stress"] = (
        (gold["is_low_balance"] == 1) & (gold["is_high_risk"] == 1)
    ).astype(int)

    # ── Guardado ─────────────────────────────────────
    GOLD_FILE.parent.mkdir(parents=True, exist_ok=True)
    gold.to_parquet(GOLD_FILE, index=False)

    print(f"  ✓ Gold: {len(gold):,} usuarios, {len(gold.columns)} features")

    return gold


if __name__ == "__main__":
    run_gold()