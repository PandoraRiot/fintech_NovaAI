"""
config.py — Fuente única de verdad para todos los parámetros del MVP.
Modifica aquí y el cambio se propaga a todos los módulos.
"""
from pathlib import Path

# ── Rutas ──────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
RAW_FILE   = DATA_DIR / "fintech_events_v4.json"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR   = DATA_DIR / "gold"

BRONZE_FILE = BRONZE_DIR / "events_bronze.parquet"
SILVER_FILE = SILVER_DIR / "events_silver.parquet"
GOLD_FILE   = GOLD_DIR   / "user_360.parquet"

# ── Parámetros de modelos ──────────────────────────────────────────────────
KMEANS_K             = 4         # Clusters de segmentación
ISOLATION_FOREST_CONTAMINATION = 0.07  # 7% de anomalías esperadas
RANDOM_STATE         = 42

# ── Umbrales de negocio (insights) ────────────────────────────────────────
HIGH_VALUE_THRESHOLD   = 2_000_000   # COP — usuario premium
LOW_BALANCE_THRESHOLD  = 100_000     # COP — balance crítico
HIGH_FAIL_RATIO        = 0.30        # 30% — tasa de fallos preocupante
DORMANT_TRANSACTIONS   = 2           # ≤ 2 tx = usuario dormido

# ── Nombres de segmentos KMeans ───────────────────────────────────────────
SEGMENT_LABELS = {
    0: ("👑", "Premium Activo",      "Alto valor, bajo riesgo — candidato VIP"),
    1: ("📈", "Activo Estándar",     "Comportamiento estable — potencial de upsell"),
    2: ("😴", "Dormido / Ocasional", "Baja frecuencia — requiere reactivación"),
    3: ("⚠️", "En Riesgo",          "Alta tasa de fallos / bajo balance — soporte urgente"),
}

# ── Colores del dashboard ─────────────────────────────────────────────────
COLORS = {
    "premium":  "#7C3AED",
    "active":   "#2563EB",
    "dormant":  "#6B7280",
    "risk":     "#DC2626",
    "anomaly":  "#F59E0B",
    "success":  "#10B981",
}

# ── Agente ────────────────────────────────────────────────────────────────
AGENT_MODEL      = "claude-sonnet-4-20250514"
AGENT_MAX_TOKENS = 400
