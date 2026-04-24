"""
FinTech Intelligence — Backend MVP
Pipeline Medallion (Bronze → Silver → Gold) + Segmentación ML
Ejecutar: uvicorn main:app --reload --port 8000
"""

import uuid
import random
import math
from datetime import datetime, timedelta
from typing import Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="FinTech Intelligence API", version="1.0.0")

# CORS abierto para desarrollo local y GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════
# MODELOS
# ══════════════════════════════════════════════════════════════════

class QuizPayload(BaseModel):
    income_range: str        # low | medium | high | premium
    spending_frequency: str  # rarely | occasionally | frequently | very_frequent
    main_category: str       # food | shopping | entertainment | transport | services
    app_usage: str           # none | basic | daily | power_user
    liquidity_issues: str    # never | rarely | occasionally | frequently


# ══════════════════════════════════════════════════════════════════
# TABLAS DE MAPEO
# ══════════════════════════════════════════════════════════════════

INCOME_MAP = {
    "low": 900_000,
    "medium": 2_200_000,
    "high": 5_000_000,
    "premium": 12_000_000,
}

FREQ_MAP = {
    "rarely": 3,
    "occasionally": 9,
    "frequently": 22,
    "very_frequent": 38,
}

LIQUIDITY_FAIL_MAP = {
    "never": 0.02,
    "rarely": 0.08,
    "occasionally": 0.20,
    "frequently": 0.42,
}

DIGITAL_SCORE_MAP = {
    "none": 10,
    "basic": 35,
    "daily": 70,
    "power_user": 95,
}

CATEGORY_WEIGHT = {
    "food": 0.38,
    "shopping": 0.30,
    "entertainment": 0.22,
    "transport": 0.18,
    "services": 0.25,
}

CATEGORY_LABELS = {
    "food": "Alimentación",
    "shopping": "Compras",
    "entertainment": "Entretenimiento",
    "transport": "Transporte",
    "services": "Servicios",
}


# ══════════════════════════════════════════════════════════════════
# BRONZE LAYER — eventos sintéticos crudos
# ══════════════════════════════════════════════════════════════════

def bronze_generate_events(payload: QuizPayload) -> list[dict]:
    """Genera entre 20-60 eventos financieros sintéticos coherentes."""
    monthly_income = INCOME_MAP.get(payload.income_range, 2_200_000)
    n_transactions  = FREQ_MAP.get(payload.spending_frequency, 9) * 3  # 3 meses
    fail_rate       = LIQUIDITY_FAIL_MAP.get(payload.liquidity_issues, 0.08)
    category_weight = CATEGORY_WEIGHT.get(payload.main_category, 0.25)

    events = []
    base_date = datetime.now() - timedelta(days=90)

    for i in range(n_transactions):
        day_offset = random.randint(0, 89)
        tx_date    = base_date + timedelta(days=day_offset)

        # Determinar categoría (mayoría en la principal)
        if random.random() < category_weight:
            cat = payload.main_category
        else:
            cats = ["food", "transport", "services", "entertainment", "shopping"]
            cat  = random.choice([c for c in cats if c != payload.main_category])

        # Monto proporcional al ingreso
        base_amount = monthly_income * random.uniform(0.01, 0.12)
        if cat == payload.main_category:
            base_amount *= 1.4  # categoría principal gasta más

        failed = random.random() < fail_rate

        events.append({
            "event_id":   str(uuid.uuid4())[:8],
            "timestamp":  tx_date.isoformat(),
            "category":   cat,
            "amount_cop": round(base_amount, -2),   # redondear a centenas
            "status":     "failed" if failed else "success",
            "channel":    "app" if payload.app_usage in ["daily", "power_user"] else "branch",
            "raw_income_range": payload.income_range,
        })

    # Agregar ingresos mensuales (3 nóminas)
    for month in range(3):
        events.append({
            "event_id":   str(uuid.uuid4())[:8],
            "timestamp":  (base_date + timedelta(days=30 * month)).isoformat(),
            "category":   "income",
            "amount_cop": round(monthly_income * random.uniform(0.95, 1.05), -3),
            "status":     "success",
            "channel":    "transfer",
            "raw_income_range": payload.income_range,
        })

    return events


# ══════════════════════════════════════════════════════════════════
# SILVER LAYER — limpieza, enriquecimiento, métricas
# ══════════════════════════════════════════════════════════════════

def silver_process(events: list[dict], payload: QuizPayload) -> dict:
    """Limpia eventos y extrae features."""
    successful  = [e for e in events if e["status"] == "success" and e["category"] != "income"]
    failed_evts = [e for e in events if e["status"] == "failed"]
    income_evts = [e for e in events if e["category"] == "income"]

    total_income = sum(e["amount_cop"] for e in income_evts) / 3   # promedio mensual
    total_spend  = sum(e["amount_cop"] for e in successful) / 3
    total_failed = sum(e["amount_cop"] for e in failed_evts) / 3

    # Gasto por categoría
    cat_spend = {}
    for e in successful:
        cat_spend[e["category"]] = cat_spend.get(e["category"], 0) + e["amount_cop"]

    # Normalizar a mensual
    cat_spend_monthly = {k: round(v / 3) for k, v in cat_spend.items()}

    fail_rate   = len(failed_evts) / max(len(events), 1)
    digital_sc  = DIGITAL_SCORE_MAP.get(payload.app_usage, 35)
    saving_rate = max(0, (total_income - total_spend) / max(total_income, 1))

    return {
        "monthly_income_cop":      round(total_income, -3),
        "monthly_spend_cop":       round(total_spend, -3),
        "monthly_failed_cop":      round(total_failed, -3),
        "monthly_balance_cop":     round(total_income - total_spend, -3),
        "monthly_transactions":    round(len(successful) / 3),
        "fail_rate_pct":           round(fail_rate * 100, 1),
        "digital_score":           digital_sc,
        "saving_rate_pct":         round(saving_rate * 100, 1),
        "top_category":            payload.main_category,
        "top_category_spend_cop":  cat_spend_monthly.get(payload.main_category, 0),
        "category_breakdown":      cat_spend_monthly,
        "n_events_raw":            len(events),
    }


# ══════════════════════════════════════════════════════════════════
# GOLD LAYER — feature vector normalizado para ML
# ══════════════════════════════════════════════════════════════════

def gold_build_features(silver: dict) -> dict:
    """Construye el vector de features para segmentación."""
    income  = silver["monthly_income_cop"]
    spend   = silver["monthly_spend_cop"]
    balance = silver["monthly_balance_cop"]

    # Normalización Min-Max aproximada (rangos Colombia)
    income_norm  = min(income  / 15_000_000, 1.0)
    spend_norm   = min(spend   / 12_000_000, 1.0)
    balance_norm = min(max(balance, 0) / 5_000_000, 1.0)
    digital_norm = silver["digital_score"] / 100
    fail_norm    = 1 - min(silver["fail_rate_pct"] / 50, 1.0)   # invertido: mayor = mejor
    saving_norm  = min(silver["saving_rate_pct"] / 40, 1.0)

    return {
        "f_income":  round(income_norm, 3),
        "f_spend":   round(spend_norm, 3),
        "f_balance": round(balance_norm, 3),
        "f_digital": round(digital_norm, 3),
        "f_fail":    round(fail_norm, 3),
        "f_saving":  round(saving_norm, 3),
        # Score compuesto (weighted sum)
        "composite_score": round(
            income_norm  * 0.30 +
            balance_norm * 0.25 +
            digital_norm * 0.20 +
            fail_norm    * 0.15 +
            saving_norm  * 0.10,
            3
        ),
    }


# ══════════════════════════════════════════════════════════════════
# ML — Segmentación (KMeans simplificado por distancia a centroides)
# ══════════════════════════════════════════════════════════════════

# Centroides representativos de 4 arquetipos financieros colombianos
# Orden features: [income, balance, digital, fail_inv, saving]
CENTROIDS = {
    "premium_activo": {
        "centroid": [0.85, 0.80, 0.90, 0.90, 0.70],
        "icon": "🏆",
        "profile_name": "Líder Financiero",
        "segment_name": "Premium Activo",
        "risk_level": "bajo",
        "risk_color": "#10b981",
        "strengths": [
            "Ingresos sólidos y estables por encima del promedio",
            "Alta adopción de herramientas digitales financieras",
            "Tasa de fallos muy baja — excelente gestión de liquidez",
            "Capacidad real de ahorro e inversión mensual",
        ],
        "opportunities": [
            "Diversificar portafolio hacia inversiones de mayor rendimiento",
            "Automatizar el ahorro con reglas inteligentes (10-20%)",
            "Considerar productos de inversión: CDT, acciones, fondos",
        ],
        "recommendations": [
            "🎯 Abre una cuenta de inversión y asigna mínimo el 15% de tus ingresos",
            "📊 Usa dashboards de gasto para optimizar la categoría principal",
            "🏦 Evalúa seguros de vida y protección patrimonial",
            "📱 Explora herramientas de inversión automatizada (robo-advisors)",
        ],
    },
    "activo_estandar": {
        "centroid": [0.45, 0.40, 0.65, 0.75, 0.35],
        "icon": "📈",
        "profile_name": "Profesional Activo",
        "segment_name": "Activo Estándar",
        "risk_level": "medio",
        "risk_color": "#2563eb",
        "strengths": [
            "Frecuencia de transacciones saludable — buena actividad financiera",
            "Adopción digital en crecimiento",
            "Ingresos estables en rango medio",
        ],
        "opportunities": [
            "Reducir gasto en categoría principal con presupuesto mensual",
            "Construir fondo de emergencia (3-6 meses de gastos)",
            "Aumentar tasa de ahorro del nivel actual al 15%",
        ],
        "recommendations": [
            "🎯 Define un presupuesto 50/30/20: necesidades/deseos/ahorro",
            "🔔 Activa alertas automáticas de gasto por categoría",
            "💰 Abre un bolsillo de ahorro separado con débito automático",
            "📱 Conecta todas tus cuentas en una app de finanzas personales",
        ],
    },
    "constructor": {
        "centroid": [0.20, 0.15, 0.40, 0.65, 0.20],
        "icon": "💼",
        "profile_name": "Constructor Constante",
        "segment_name": "Perfil en Desarrollo",
        "risk_level": "medio-alto",
        "risk_color": "#f59e0b",
        "strengths": [
            "Conciencia financiera activa — completaste este análisis",
            "Patrón de gasto identificado y manejable",
        ],
        "opportunities": [
            "Estabilizar flujo de caja mensual con presupuesto básico",
            "Reducir dependencia de crédito informal o cuotas",
            "Incrementar ingresos con fuentes adicionales o mejora salarial",
        ],
        "recommendations": [
            "🎯 Registra TODOS tus gastos durante 30 días (app o libreta)",
            "🚨 Crea un fondo de emergencia mínimo de $500.000 COP",
            "📋 Negocia fechas de pago de deudas para evitar cargos extra",
            "💡 Explora capacitaciones para mejora salarial en tu sector",
        ],
    },
    "explorador": {
        "centroid": [0.10, 0.05, 0.20, 0.45, 0.05],
        "icon": "🌱",
        "profile_name": "Explorador Financiero",
        "segment_name": "Perfil en Crecimiento",
        "risk_level": "alto",
        "risk_color": "#ef4444",
        "strengths": [
            "Dar el primer paso con este análisis es señal de conciencia",
            "Oportunidad de construir hábitos financieros desde cero",
        ],
        "opportunities": [
            "Eliminar gastos hormiga — pequeños gastos diarios que suman",
            "Acceder a educación financiera básica gratuita",
            "Formalizar ingresos para acceder a productos bancarios",
        ],
        "recommendations": [
            "🎯 Aplica la regla del sobre: divide tu dinero físico por categoría",
            "📚 Toma el curso gratuito de educación financiera del Banco de la República",
            "🏦 Abre una cuenta de ahorros digital (Nequi/Daviplata) — es gratis",
            "🔴 Prioriza: primero alimento y vivienda, luego el resto",
        ],
    },
}


def ml_segment(features: dict) -> tuple[str, dict]:
    """Asigna arquetipo por distancia euclidiana al centroide más cercano."""
    fvec = [
        features["f_income"],
        features["f_balance"],
        features["f_digital"],
        features["f_fail"],
        features["f_saving"],
    ]

    best_segment = None
    best_dist    = float("inf")

    for seg_name, seg_data in CENTROIDS.items():
        centroid = seg_data["centroid"]
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(fvec, centroid)))
        if dist < best_dist:
            best_dist    = dist
            best_segment = seg_name

    return best_segment, CENTROIDS[best_segment]


# ══════════════════════════════════════════════════════════════════
# ENDPOINT PRINCIPAL
# ══════════════════════════════════════════════════════════════════

@app.post("/api/v1/quiz/submit")
async def submit_quiz(payload: QuizPayload) -> dict[str, Any]:
    """
    Pipeline completo:
    1. Bronze  → Genera eventos financieros sintéticos
    2. Silver  → Limpia y extrae métricas
    3. Gold    → Construye feature vector normalizado
    4. ML      → Segmentación por distancia euclidiana a centroides
    5. Output  → Perfil personalizado con recomendaciones
    """

    # ── BRONZE ──
    bronze_events = bronze_generate_events(payload)

    # ── SILVER ──
    silver_metrics = silver_process(bronze_events, payload)

    # ── GOLD ──
    gold_features = gold_build_features(silver_metrics)

    # ── ML ──
    segment_key, segment_data = ml_segment(gold_features)

    # ── RESPONSE ──
    user_id = f"FI-{uuid.uuid4().hex[:8].upper()}"

    summary = (
        f"Con ingresos estimados de "
        f"${silver_metrics['monthly_income_cop']:,.0f} COP/mes y "
        f"{silver_metrics['monthly_transactions']} transacciones mensuales, "
        f"tu perfil es {segment_data['profile_name']}. "
        f"Tu gasto principal es {CATEGORY_LABELS.get(payload.main_category, payload.main_category)} "
        f"(~${silver_metrics['top_category_spend_cop']:,.0f} COP/mes) "
        f"con una tasa de ahorro del {silver_metrics['saving_rate_pct']}%."
    )

    return {
        "user_id":       user_id,
        "profile_name":  segment_data["profile_name"],
        "segment_icon":  segment_data["icon"],
        "segment_name":  segment_data["segment_name"],
        "risk_level":    segment_data["risk_level"],
        "risk_color":    segment_data["risk_color"],
        "summary":       summary,
        "strengths":     segment_data["strengths"],
        "opportunities": segment_data["opportunities"],
        "recommendations": segment_data["recommendations"],
        "metrics": {
            "estimated_monthly_income_cop":  silver_metrics["monthly_income_cop"],
            "estimated_monthly_spend_cop":   silver_metrics["monthly_spend_cop"],
            "estimated_balance_cop":         silver_metrics["monthly_balance_cop"],
            "monthly_transactions":          silver_metrics["monthly_transactions"],
            "fail_rate_pct":                 silver_metrics["fail_rate_pct"],
            "saving_rate_pct":               silver_metrics["saving_rate_pct"],
            "digital_score":                 silver_metrics["digital_score"],
            "composite_score":               gold_features["composite_score"],
            "main_category":                 payload.main_category,
            "n_synthetic_events":            len(bronze_events),
        },
        "pipeline_debug": {
            "bronze_events_count":    len(bronze_events),
            "silver_metrics":         silver_metrics,
            "gold_features":          gold_features,
            "ml_segment_assigned":    segment_key,
        },
        "cta_url": "https://www.youtube.com/watch?v=Ke1hc862LAs&feature=youtu.be",
    }


@app.get("/")
def root():
    return {"status": "ok", "api": "FinTech Intelligence", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}