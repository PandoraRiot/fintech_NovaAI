"""
pipeline/bronze.py — Capa Bronze
Ingesta el JSON crudo, aplana la estructura nested y persiste en Parquet.
PRINCIPIO: nunca modifica valores de negocio.
"""
import json
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RAW_FILE, BRONZE_FILE


def flatten_event(evt: dict) -> dict:
    """Aplana un evento JSON (3 niveles) en un diccionario plano."""
    d = evt.get("detail", {})
    p = d.get("payload", {})
    loc = p.get("location", {})
    meta = d.get("metadata", {})

    return {
        # Evento
        "event_id":        d.get("id"),
        "event_type":      d.get("event"),
        "event_status":    d.get("eventStatus"),
        "transaction_type": d.get("transactionType"),
        # Usuario
        "userId":          p.get("userId"),
        "name":            p.get("name"),
        "age":             p.get("age"),
        "email":           p.get("email"),
        "segment":         p.get("segment"),
        "city_payload":    p.get("city"),
        # Financiero
        "amount":          p.get("amount"),
        "currency":        p.get("currency"),
        "merchant":        p.get("merchant"),
        "category":        p.get("category"),
        "payment_method":  p.get("paymentMethod"),
        "installments":    p.get("installments"),
        "balance_before":  p.get("balanceBefore"),
        "balance_after":   p.get("balanceAfter"),
        "timestamp":       p.get("timestamp"),
        # Ubicación
        "city_location":   loc.get("city"),
        "country":         loc.get("country"),
        # Metadata
        "device":          meta.get("device"),
        "os":              meta.get("os"),
        "channel":         meta.get("channel"),
        "ip":              meta.get("ip"),
    }


def run_bronze(enrich: bool = True) -> pd.DataFrame:
    """
    Ejecuta la capa Bronze: JSON → Parquet.
    Si enrich=True, llama a las APIs open source para enriquecer.
    """
    print("▶ Bronze: leyendo JSON crudo...")
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    rows = [flatten_event(e) for e in raw]
    df = pd.DataFrame(rows)

    # ── Enriquecimiento con APIs open source ─────────────────────────────
    if enrich:
        try:
            from enrichment.apis import enrich_events_dataframe
            print("  📡 Enriqueciendo con APIs open source...")
            df = enrich_events_dataframe(df, enable_geo=True, enable_fx=True)
        except Exception as e:
            print(f"  ⚠️  Enriquecimiento omitido (sin conectividad): {e}")
            df["amount_cop"] = df["amount"].fillna(0)
            df["usd_cop_rate"] = 4150.0

    BRONZE_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(BRONZE_FILE, index=False)
    print(f"  ✓ Bronze: {len(df):,} eventos, {len(df.columns)} columnas → {BRONZE_FILE.name}")
    return df


if __name__ == "__main__":
    run_bronze()
