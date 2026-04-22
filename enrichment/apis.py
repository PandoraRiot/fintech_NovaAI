"""
enrichment/apis.py — APIs Open Source (SIMPLIFICADO + BTC)

APIs:
  1. Frankfurter → Tasas de cambio (BCE europeo, sin key)
  2. ip-api       → Geolocalización, sin key
  3. CoinGecko    → Precio BTC, key presente


"""

import time
import json
import requests
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 5
MAX_RETRIES = 2

# ── CACHE ─────────────────────────────────────────────
_rate_cache = {}
_rate_cache_time = None

_btc_cache = None
_btc_cache_time = None

CACHE_TTL_MINUTES = 60


# ─────────────────────────────────────────────────────
# UTIL
# ─────────────────────────────────────────────────────
def _get(url: str, params: dict = None) -> Optional[dict]:
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception:
            time.sleep(0.3 * (attempt + 1))
    return None


# ─────────────────────────────────────────────────────
# 1. TASAS DE CAMBIO — Frankfurter.app (Banco Central Europeo)
#    Endpoint: https://api.frankfurter.app/latest?from=USD&to=COP
#    Límite: sin límite, datos actualizados cada día hábil
#    Open Source: datos del BCE, API de código abierto
# ─────────────────────────────────────────────────────
def get_exchange_rates(base: str = "USD") -> Dict[str, float]:
    global _rate_cache, _rate_cache_time

    if (
        _rate_cache
        and _rate_cache_time
        and datetime.now() - _rate_cache_time < timedelta(minutes=CACHE_TTL_MINUTES)
    ):
        return _rate_cache

    data = _get("https://api.frankfurter.app/latest", params={"from": base})

    if data and "rates" in data:
        rates = data["rates"]
        rates[base] = 1.0
        _rate_cache = rates
        _rate_cache_time = datetime.now()
        return rates

    # fallback
    return {"USD": 1.0, "COP": 4150.0}


def convert_to_cop(amount: float, from_currency: str) -> float:
    if from_currency == "COP":
        return amount

    rates = get_exchange_rates("USD")

    if from_currency in rates and "COP" in rates:
        usd = amount / rates[from_currency]
        return usd * rates["COP"]

    return amount


def get_usd_cop_rate() -> float:
    rates = get_exchange_rates("USD")
    return float(rates.get("COP", 4150.0))


# ─────────────────────────────────────────────────────
# 2. BTC PRICE (CoinGecko)
# ─────────────────────────────────────────────────────
def get_btc_price_usd() -> float:
    global _btc_cache, _btc_cache_time

    if (
        _btc_cache
        and _btc_cache_time
        and datetime.now() - _btc_cache_time < timedelta(minutes=CACHE_TTL_MINUTES)
    ):
        return _btc_cache

    data = _get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": "bitcoin", "vs_currencies": "usd"},
    )

    if data and "bitcoin" in data:
        price = data["bitcoin"]["usd"]
        _btc_cache = price
        _btc_cache_time = datetime.now()
        return price

    # fallback
    return 60000.0


# ─────────────────────────────────────────────────────
# 3. GEO (ip-api)
# ─────────────────────────────────────────────────────
def geolocate_ip(ip: str) -> Dict[str, Any]:

    if (
        not ip
        or str(ip).startswith(("192.168.", "10.", "172.", "127.", "0."))
    ):
        return {"geo_country": "Colombia", "geo_city": ""}

    data = _get(f"http://ip-api.com/json/{ip}")

    if data and data.get("status") == "success":
        return {
            "geo_country": data.get("country", ""),
            "geo_city": data.get("city", ""),
        }

    return {"geo_country": "", "geo_city": ""}


# ─────────────────────────────────────────────────────
# 4. MAIN ENRICHMENT
# ─────────────────────────────────────────────────────
def enrich_events_dataframe(df, enable_geo=True, enable_fx=True):

    import pandas as pd

    result = df.copy()

    # ── FX ───────────────────────────────────────────
    if enable_fx:
        usd_cop = get_usd_cop_rate()
        result["usd_cop_rate"] = usd_cop

        result["amount_cop"] = result.apply(
            lambda r: convert_to_cop(r.get("amount", 0), r.get("currency", "COP")),
            axis=1,
        )
    else:
        result["usd_cop_rate"] = 4150.0
        result["amount_cop"] = result["amount"]

    # ── BTC PRICE (NUEVO) ────────────────────────────
    btc_price = get_btc_price_usd()
    result["btc_price_usd"] = btc_price

    # feature adicional interesante
    result["amount_btc"] = result["amount_cop"] / (btc_price * result["usd_cop_rate"])

    print(f"  ✓ BTC price: ${btc_price:,.0f}")

    # ── GEO ──────────────────────────────────────────
    if enable_geo and "ip" in result.columns:
        geo_data = result["ip"].apply(geolocate_ip).apply(pd.Series)
        result = pd.concat([result, geo_data], axis=1)

    return result

#----------------------------------
#VERIFICACION DE DISPONIBILIDAD DE API'S
#-------------------------------------
def check_api_health() -> Dict[str, str]:
    """
    Verifica disponibilidad de APIs externas.
    Útil para debugging, dashboards o monitoreo.
    """

    status = {}

    # ── Frankfurter (FX) ─────────────────────────────
    fx = _get("https://api.frankfurter.app/latest", params={"from": "USD"})
    status["frankfurter_fx"] = (
        "✅ online" if fx and "rates" in fx
        else "⚠️ offline (usando fallback)"
    )

    # ── CoinGecko (BTC) ──────────────────────────────
    btc = _get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": "bitcoin", "vs_currencies": "usd"},
    )
    status["coingecko_btc"] = (
        "✅ online" if btc and "bitcoin" in btc
        else "⚠️ offline (usando fallback)"
    )

    # ── ip-api (Geo) ─────────────────────────────────
    geo = _get("http://ip-api.com/json/8.8.8.8")
    status["ipapi_geo"] = (
        "✅ online" if geo and geo.get("status") == "success"
        else "⚠️ offline"
    )

    return status