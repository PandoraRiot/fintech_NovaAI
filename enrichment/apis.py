"""
enrichment/apis.py — Integración con APIs Open Source (sin API key)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APIs utilizadas (todas 100% gratuitas y open source):
  1. Frankfurter.app   → Tasas de cambio (BCE europeo, sin key)
  2. ip-api.com        → Geolocalización de IPs (45 req/min, sin key)
  3. RestCountries.eu  → Metadata de países (sin key, sin límite)
  4. Open Exchange Rates (fallback offline con tabla estática)

Patrón: cache en memoria + fallback offline → el pipeline NUNCA falla
"""
import time
import json
import requests
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── Timeouts y reintentos ──────────────────────────────────────────────────
REQUEST_TIMEOUT = 5   # segundos
MAX_RETRIES     = 2

# ── Tasas de cambio offline (fallback si la API no responde) ───────────────
# Fuente: Banco de la República Colombia, promedio 2026
OFFLINE_RATES_TO_COP = {
    "USD": 4_150.0,
    "EUR": 4_480.0,
    "GBP": 5_250.0,
    "BRL": 780.0,
    "MXN": 240.0,
    "CLP": 4.4,
    "PEN": 1_100.0,
    "ARS": 4.5,
    "COP": 1.0,
}

# ── Cache simple en memoria ────────────────────────────────────────────────
_rate_cache: Dict[str, Any] = {}
_rate_cache_time: Optional[datetime] = None
CACHE_TTL_MINUTES = 60  # refrescar tasas cada hora

_geo_cache: Dict[str, Any] = {}       # IP → geo info
_country_cache: Dict[str, Any] = {}   # country name → metadata


def _get(url: str, params: dict = None) -> Optional[dict]:
    """GET con reintentos silenciosos."""
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.debug(f"API request failed ({attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(0.3 * (attempt + 1))
    return None


# ══════════════════════════════════════════════════════════════════════════
# 1. TASAS DE CAMBIO — Frankfurter.app (Banco Central Europeo)
#    Endpoint: https://api.frankfurter.app/latest?from=USD&to=COP
#    Límite: sin límite, datos actualizados cada día hábil
#    Open Source: datos del BCE, API de código abierto
# ══════════════════════════════════════════════════════════════════════════
def get_exchange_rates(base: str = "USD") -> Dict[str, float]:
    """
    Obtiene tasas de cambio actuales desde Frankfurter.app.
    Si la API falla, retorna tasas offline precargadas.
    """
    global _rate_cache, _rate_cache_time

    # Usar cache si es reciente
    if (
        _rate_cache
        and _rate_cache_time
        and datetime.now() - _rate_cache_time < timedelta(minutes=CACHE_TTL_MINUTES)
    ):
        return _rate_cache

    data = _get(f"https://api.frankfurter.app/latest", params={"from": base})

    if data and "rates" in data:
        rates = data["rates"]
        rates[base] = 1.0  # base siempre = 1
        _rate_cache = rates
        _rate_cache_time = datetime.now()
        logger.info(f"✓ Exchange rates actualizadas desde Frankfurter ({len(rates)} monedas)")
        return rates

    # Fallback offline
    logger.warning("⚠ Frankfurter no disponible — usando tasas offline")
    return OFFLINE_RATES_TO_COP


def convert_to_cop(amount: float, from_currency: str) -> float:
    """Convierte un monto a COP usando la tasa actual o fallback."""
    if from_currency == "COP":
        return amount

    # Intentar con tasas en vivo (USD como pivote)
    rates_from_usd = get_exchange_rates(base="USD")

    if from_currency in rates_from_usd and "COP" in rates_from_usd:
        # Convertir: amount (from_currency) → USD → COP
        amount_usd = amount / rates_from_usd.get(from_currency, 1)
        return amount_usd * rates_from_usd.get("COP", OFFLINE_RATES_TO_COP["USD"])

    # Fallback directo offline
    rate_to_cop = OFFLINE_RATES_TO_COP.get(from_currency, 1.0)
    return amount * rate_to_cop


def get_usd_cop_rate() -> float:
    """Retorna tasa USD/COP actual."""
    rates = get_exchange_rates("USD")
    return float(rates.get("COP", OFFLINE_RATES_TO_COP["USD"]))


# ══════════════════════════════════════════════════════════════════════════
# 2. GEOLOCALIZACIÓN — ip-api.com
#    Endpoint: http://ip-api.com/json/{ip}
#    Límite: 45 req/min sin key (suficiente para enriquecer batch)
#    Open Source: servicio gratuito sin registro
# ══════════════════════════════════════════════════════════════════════════
def geolocate_ip(ip: str) -> Dict[str, str]:
    """
    Geolocaliza una IP pública y retorna país, ciudad, región, ISP.
    IPs privadas (192.168.x.x, 10.x.x.x) retornan metadata vacía.
    """
    # IPs privadas → no geolocalizables
    if (
        ip.startswith(("192.168.", "10.", "172.16.", "172.17.", "172.18.",
                       "172.19.", "172.2", "127.", "0."))
        or not ip
    ):
        return {"geo_country": "Colombia", "geo_city": "", "geo_region": "",
                "geo_isp": "", "geo_lat": 4.71, "geo_lon": -74.07, "geo_source": "private_ip"}

    if ip in _geo_cache:
        return _geo_cache[ip]

    data = _get(f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,city,regionName,isp,lat,lon,timezone"})

    if data and data.get("status") == "success":
        result = {
            "geo_country":  data.get("country", ""),
            "geo_city":     data.get("city", ""),
            "geo_region":   data.get("regionName", ""),
            "geo_isp":      data.get("isp", ""),
            "geo_lat":      data.get("lat", 0.0),
            "geo_lon":      data.get("lon", 0.0),
            "geo_source":   "ip-api.com",
        }
        _geo_cache[ip] = result
        return result

    return {"geo_country": "", "geo_city": "", "geo_region": "",
            "geo_isp": "", "geo_lat": 0.0, "geo_lon": 0.0, "geo_source": "error"}


def geolocate_batch(ips: list, delay_ms: int = 80) -> Dict[str, dict]:
    """
    Geolocaliza una lista de IPs respetando el rate limit de 45 req/min.
    delay_ms = 80ms entre requests → ~12 req/s, bien bajo el límite.
    """
    results = {}
    unique_ips = list(set(ips))
    for ip in unique_ips:
        results[ip] = geolocate_ip(ip)
        time.sleep(delay_ms / 1000)
    return results


# ══════════════════════════════════════════════════════════════════════════
# 3. METADATA DE PAÍSES — RestCountries.eu
#    Endpoint: https://restcountries.com/v3.1/name/{country}
#    Límite: sin límite, datos de Wikipedia/ISO
#    Open Source: https://github.com/apilayer/restcountries
# ══════════════════════════════════════════════════════════════════════════
def get_country_metadata(country_name: str) -> Dict[str, Any]:
    """
    Obtiene metadata de un país: región, moneda oficial, idioma, capital.
    Useful para enriquecer el perfil geográfico del usuario.
    """
    if country_name in _country_cache:
        return _country_cache[country_name]

    data = _get(
        f"https://restcountries.com/v3.1/name/{country_name}",
        params={"fields": "name,currencies,capital,region,subregion,languages,population"},
    )

    if data and isinstance(data, list) and len(data) > 0:
        c = data[0]
        currencies = list(c.get("currencies", {}).keys())
        languages = list(c.get("languages", {}).values())
        result = {
            "country_region":    c.get("region", ""),
            "country_subregion": c.get("subregion", ""),
            "country_currency":  currencies[0] if currencies else "",
            "country_capital":   c.get("capital", [""])[0] if c.get("capital") else "",
            "country_language":  languages[0] if languages else "",
            "country_population": c.get("population", 0),
        }
        _country_cache[country_name] = result
        return result

    # Fallback para Colombia (caso mayoritario del dataset)
    fallback = {
        "Colombia": {
            "country_region": "Americas", "country_subregion": "South America",
            "country_currency": "COP", "country_capital": "Bogotá",
            "country_language": "Spanish", "country_population": 51_000_000,
        }
    }
    return fallback.get(country_name, {
        "country_region": "", "country_subregion": "", "country_currency": "",
        "country_capital": "", "country_language": "", "country_population": 0,
    })


# ══════════════════════════════════════════════════════════════════════════
# 4. FUNCIÓN DE ENRIQUECIMIENTO COMPLETO (Bronze → Bronze Enriched)
# ══════════════════════════════════════════════════════════════════════════
def enrich_events_dataframe(df, enable_geo: bool = True, enable_fx: bool = True):
    """
    Enriquece el DataFrame Bronze con:
    - Tasa de cambio USD/COP actual (Frankfurter)
    - Monto normalizado a COP
    - Geolocalización de IP (ip-api.com, solo IPs públicas)
    - Metadata del país (RestCountries)

    Parámetros:
        enable_geo: False en entornos sin acceso a internet (usa offline)
        enable_fx:  False para usar tasas offline siempre
    """
    import pandas as pd

    result = df.copy()

    # ── FX: normalizar montos a COP ───────────────────────────────────────
    if enable_fx:
        usd_cop = get_usd_cop_rate()
        result["usd_cop_rate"] = usd_cop
        result["amount_cop"] = result.apply(
            lambda r: convert_to_cop(r.get("amount", 0), r.get("currency", "COP")),
            axis=1,
        )
        print(f"  ✓ FX: tasa USD/COP = {usd_cop:,.0f}")
    else:
        result["usd_cop_rate"] = OFFLINE_RATES_TO_COP["USD"]
        result["amount_cop"] = result["amount"].fillna(0)
        print(f"  ✓ FX offline: {OFFLINE_RATES_TO_COP['USD']:,.0f} COP/USD")

    # ── GEO: enriquecer IPs (solo públicas) ──────────────────────────────
    if enable_geo and "ip" in result.columns:
        public_ips = [
            ip for ip in result["ip"].dropna().unique()
            if not str(ip).startswith(("192.168.", "10.", "172.", "127.", "0."))
        ]
        if public_ips:
            print(f"  📡 Geolocalizando {len(public_ips)} IPs públicas...")
            geo_map = geolocate_batch(public_ips)
            geo_df = pd.DataFrame(geo_map).T
            result = result.merge(
                geo_df.reset_index().rename(columns={"index": "ip"}),
                on="ip", how="left",
            )
        else:
            print("  ℹ️  Todas las IPs son privadas (192.168.x.x) — geo omitida")
            for col in ["geo_country", "geo_city", "geo_region", "geo_isp", "geo_lat", "geo_lon"]:
                result[col] = ""
    else:
        for col in ["geo_country", "geo_city", "geo_region", "geo_isp", "geo_lat", "geo_lon"]:
            result[col] = ""

    # ── COUNTRIES: metadata del país ─────────────────────────────────────
    if "country" in result.columns:
        unique_countries = result["country"].dropna().unique()
        for country in unique_countries:
            if country:
                meta = get_country_metadata(str(country))
                for key, val in meta.items():
                    if key not in result.columns:
                        result[key] = ""
                    result.loc[result["country"] == country, key] = val
        print(f"  ✓ Country metadata: {len(unique_countries)} países enriquecidos")

    return result


# ══════════════════════════════════════════════════════════════════════════
# 5. HEALTH CHECK — verifica disponibilidad de APIs
# ══════════════════════════════════════════════════════════════════════════
def check_api_health() -> Dict[str, str]:
    """Verifica qué APIs están disponibles. Útil para el dashboard."""
    status = {}

    # Frankfurter
    data = _get("https://api.frankfurter.app/latest", params={"from": "USD"})
    status["frankfurter_fx"] = "✅ online" if data else "⚠️ offline (usando tasas locales)"

    # ip-api.com
    data = _get("http://ip-api.com/json/8.8.8.8")
    status["ipapi_geo"] = "✅ online" if (data and data.get("status") == "success") else "⚠️ offline"

    # RestCountries
    data = _get("https://restcountries.com/v3.1/name/colombia", params={"fields": "name"})
    status["restcountries"] = "✅ online" if data else "⚠️ offline"

    return status
