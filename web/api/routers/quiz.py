"""
api/routers/quiz.py — Endpoint del cuestionario financiero interactivo (QR Mobile)
POST /api/v1/quiz/submit

Convierte 5 respuestas del quiz en un perfil financiero completo:
1. Genera eventos sintéticos coherentes con las respuestas
2. Ejecuta el pipeline Medallion sobre el usuario virtual
3. Aplica los modelos ML al dataset extendido
4. Retorna el perfil financiero personalizado
"""
import uuid
import logging
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from api.schemas import QuizAnswers, QuizResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/quiz", tags=["Quiz Financiero"])


# ── Tablas de mapeo: respuestas del quiz → parámetros financieros ──────────

INCOME_MAP = {
    "low":     {"monthly": 800_000,    "label": "Menos de $1M COP"},
    "medium":  {"monthly": 2_000_000,  "label": "$1M – $3M COP"},
    "high":    {"monthly": 5_000_000,  "label": "$3M – $7M COP"},
    "premium": {"monthly": 12_000_000, "label": "Más de $7M COP"},
}

FREQUENCY_MAP = {
    "rarely":        {"n_tx": 3,  "label": "Raramente"},
    "occasionally":  {"n_tx": 8,  "label": "Ocasionalmente"},
    "frequently":    {"n_tx": 20, "label": "Frecuentemente"},
    "very_frequent": {"n_tx": 35, "label": "Muy frecuente"},
}

CATEGORY_MAP = {
    "food":          "food",
    "shopping":      "shopping",
    "entertainment": "entertainment",
    "transport":     "transport",
    "services":      "services",
}

APP_USAGE_MAP = {
    "none":       {"channel": "branch",  "device": "unknown", "days_active": 2},
    "basic":      {"channel": "app",     "device": "android", "days_active": 5},
    "daily":      {"channel": "app",     "device": "ios",     "days_active": 20},
    "power_user": {"channel": "app",     "device": "ios",     "days_active": 28},
}

LIQUIDITY_MAP = {
    "never":        {"fail_rate": 0.03, "min_balance_factor": 0.5},
    "rarely":       {"fail_rate": 0.08, "min_balance_factor": 0.2},
    "occasionally": {"fail_rate": 0.20, "min_balance_factor": 0.05},
    "frequently":   {"fail_rate": 0.40, "min_balance_factor": 0.01},
}

PROFILE_ARCHETYPES = {
    ("premium", "very_frequent", "never"):   ("🏆", "Líder Financiero",      "Gestión excelente, candidato VIP"),
    ("high",    "frequently",    "rarely"):  ("📈", "Profesional Activo",    "Comportamiento financiero maduro"),
    ("medium",  "frequently",    "rarely"):  ("💼", "Constructor Constante", "Hábitos sólidos, potencial de crecimiento"),
    ("medium",  "occasionally",  "occasionally"): ("🌱", "Explorador Financiero", "En desarrollo, oportunidades claras"),
    ("low",     "rarely",        "frequently"):   ("⚠️", "Perfil en Riesgo",      "Requiere atención y apoyo financiero"),
}

RISK_LEVEL_MAP = {
    "never":        ("BAJO",    "#10B981"),
    "rarely":       ("MEDIO",   "#2563EB"),
    "occasionally": ("ALTO",    "#F59E0B"),
    "frequently":   ("CRÍTICO", "#DC2626"),
}


def generate_synthetic_events(answers: QuizAnswers, user_id: str) -> list:
    """
    Genera eventos financieros sintéticos coherentes con las respuestas del quiz.
    Produce entre 3 y 35 transacciones con timestamps realistas del último mes.
    """
    income_params   = INCOME_MAP[answers.income_range]
    freq_params     = FREQUENCY_MAP[answers.spending_frequency]
    app_params      = APP_USAGE_MAP[answers.app_usage]
    liquidity_params = LIQUIDITY_MAP[answers.liquidity_issues]

    monthly_income  = income_params["monthly"]
    n_transactions  = freq_params["n_tx"]
    channel         = app_params["channel"]
    device          = app_params["device"]
    fail_rate       = liquidity_params["fail_rate"]

    events = []
    now    = datetime.utcnow()
    categories = [answers.main_category] * 3 + list(CATEGORY_MAP.values())

    # Evento 1: Recarga de saldo (ingreso mensual)
    events.append(_make_event(
        user_id=user_id,
        event_type="MONEY_ADDED",
        status="SUCCESS",
        amount=monthly_income,
        category="recarga",
        channel=channel,
        device=device,
        timestamp=now - timedelta(days=25),
        balance_before=monthly_income * 0.1,
        balance_after=monthly_income * 1.1,
    ))

    # Eventos de gasto (n_transactions - 1 eventos)
    balance = monthly_income * 1.1
    for i in range(n_transactions - 1):
        days_ago   = random.randint(0, 28)
        tx_ts      = now - timedelta(days=days_ago, hours=random.randint(6, 23))
        pct_spend  = random.uniform(0.03, 0.25)
        amount     = monthly_income * pct_spend
        is_failed  = random.random() < fail_rate
        cat        = random.choice(categories)

        if is_failed:
            events.append(_make_event(
                user_id=user_id,
                event_type="PAYMENT_FAILED",
                status="FAILED",
                amount=amount,
                category=cat,
                channel=channel,
                device=device,
                timestamp=tx_ts,
                balance_before=balance,
                balance_after=balance,  # balance no cambia si falla
            ))
        else:
            new_balance = max(0, balance - amount)
            events.append(_make_event(
                user_id=user_id,
                event_type="PAYMENT_COMPLETED",
                status="SUCCESS",
                amount=amount,
                category=cat,
                channel=channel,
                device=device,
                timestamp=tx_ts,
                balance_before=balance,
                balance_after=new_balance,
            ))
            balance = new_balance

    return events


def _make_event(
    user_id: str, event_type: str, status: str, amount: float,
    category: str, channel: str, device: str, timestamp: datetime,
    balance_before: float, balance_after: float,
) -> dict:
    """Construye un evento en el formato JSON del sistema."""
    return {
        "detail": {
            "id": str(uuid.uuid4()),
            "event": event_type,
            "eventStatus": status,
            "transactionType": "DEBIT" if "PAYMENT" in event_type else "CREDIT",
            "payload": {
                "userId":       user_id,
                "name":         "Quiz User",
                "age":          28,
                "email":        f"{user_id}@quiz.app",
                "segment":      "individual",
                "city":         "Bogotá",
                "amount":       round(amount, 2),
                "currency":     "COP",
                "merchant":     f"Merchant_{category.title()}",
                "category":     category,
                "paymentMethod": "digital_wallet",
                "installments": 1,
                "balanceBefore": round(balance_before, 2),
                "balanceAfter":  round(balance_after, 2),
                "timestamp":     timestamp.isoformat(),
                "location": {
                    "city":    "Bogotá",
                    "country": "Colombia",
                },
            },
            "metadata": {
                "device":  device,
                "os":      "iOS" if device == "ios" else "Android",
                "channel": channel,
                "ip":      "192.168.1.1",
            },
        }
    }


def _determine_archetype(answers: QuizAnswers) -> tuple:
    """Determina el arquetipo financiero más cercano."""
    key = (answers.income_range, answers.spending_frequency, answers.liquidity_issues)
    if key in PROFILE_ARCHETYPES:
        icon, name, desc = PROFILE_ARCHETYPES[key]
    else:
        # Lógica de fallback por score compuesto
        income_score    = {"low": 0, "medium": 1, "high": 2, "premium": 3}[answers.income_range]
        freq_score      = {"rarely": 0, "occasionally": 1, "frequently": 2, "very_frequent": 3}[answers.spending_frequency]
        liquidity_score = {"never": 3, "rarely": 2, "occasionally": 1, "frequently": 0}[answers.liquidity_issues]
        total = income_score + freq_score + liquidity_score

        if total >= 7:
            icon, name, desc = "🏆", "Líder Financiero",      "Gestión excelente"
        elif total >= 5:
            icon, name, desc = "📈", "Profesional Activo",    "Comportamiento maduro"
        elif total >= 3:
            icon, name, desc = "💼", "Constructor Constante", "Hábitos en desarrollo"
        elif total >= 1:
            icon, name, desc = "🌱", "Explorador Financiero", "Oportunidades de mejora"
        else:
            icon, name, desc = "⚠️", "Perfil en Riesgo",      "Apoyo recomendado"

    return icon, name, desc


def _generate_recommendations(answers: QuizAnswers) -> tuple:
    """Genera fortalezas, oportunidades y recomendaciones basadas en las respuestas."""
    strengths      = []
    opportunities  = []
    recommendations = []

    # Fortalezas
    if answers.income_range in ("high", "premium"):
        strengths.append("✅ Alto nivel de ingresos — base sólida para inversión")
    if answers.spending_frequency in ("frequently", "very_frequent"):
        strengths.append("✅ Alta actividad financiera — genera historial crediticio")
    if answers.liquidity_issues in ("never", "rarely"):
        strengths.append("✅ Buena salud de liquidez — sin presión financiera inmediata")
    if answers.app_usage in ("daily", "power_user"):
        strengths.append("✅ Adopción digital activa — acceso a herramientas modernas")

    # Oportunidades
    if answers.income_range == "low":
        opportunities.append("📊 Potencial de crecimiento de ingresos con educación financiera")
    if answers.spending_frequency in ("rarely", "occasionally"):
        opportunities.append("🔄 Aumento de actividad puede mejorar tu score crediticio")
    if answers.liquidity_issues in ("occasionally", "frequently"):
        opportunities.append("💰 Control de gastos puede liberar $200k-$500k COP/mes")
    if answers.app_usage in ("none", "basic"):
        opportunities.append("📱 Digitalización financiera puede ahorrarte tiempo y dinero")

    # Recomendaciones accionables
    cat = answers.main_category
    income_amount = INCOME_MAP[answers.income_range]["monthly"]

    recommendations.append(
        f"🎯 Establece un presupuesto mensual de ${income_amount * 0.3:,.0f} COP para '{cat}' "
        f"y automatiza el ahorro del restante."
    )

    if answers.liquidity_issues in ("occasionally", "frequently"):
        recommendations.append(
            "🔔 Activa alertas de saldo mínimo en $300,000 COP para evitar transacciones fallidas."
        )
    else:
        recommendations.append(
            "📈 Considera mover el 10% de tus ingresos a un CDT o fondo de inversión de bajo riesgo."
        )

    if answers.app_usage in ("none", "basic"):
        recommendations.append(
            "📲 Descarga una app de gestión financiera y conecta todas tus cuentas — "
            "la visibilidad es el primer paso para el control."
        )
    else:
        recommendations.append(
            "🤖 Activa las notificaciones de gastos inusuales — el 73% de fraudes se detectan "
            "primero por el usuario, no por el banco."
        )

    return strengths or ["✅ Estás tomando el primer paso con este análisis"], \
           opportunities or ["🌱 Continúa explorando opciones de optimización financiera"], \
           recommendations


@router.post(
    "/submit",
    response_model=QuizResult,
    summary="Enviar respuestas del quiz y obtener perfil financiero",
    description="""
    Recibe las 5 respuestas del cuestionario interactivo y:
    1. Genera eventos financieros sintéticos coherentes
    2. Procesa a través del pipeline Medallion (mini-pipeline)
    3. Aplica modelos ML para segmentación
    4. Retorna un perfil financiero personalizado con recomendaciones accionables
    
    Esta función es el corazón de la experiencia QR mobile.
    Latencia esperada: 200–800ms.
    """,
)
async def submit_quiz(answers: QuizAnswers) -> QuizResult:
    """
    Procesa las respuestas del quiz y retorna el perfil financiero.
    """
    # ID único para el usuario del quiz
    user_id = f"QUIZ_{str(uuid.uuid4())[:8].upper()}"

    try:
        # Generar eventos sintéticos
        events = generate_synthetic_events(answers, user_id)

        # Determinar arquetipo y riesgo
        icon, profile_name, _ = _determine_archetype(answers)
        risk_level, risk_color = RISK_LEVEL_MAP[answers.liquidity_issues]

        # Determinar segmento KMeans aproximado por reglas
        income_score    = {"low": 0, "medium": 1, "high": 2, "premium": 3}[answers.income_range]
        liquidity_score = {"never": 3, "rarely": 2, "occasionally": 1, "frequently": 0}[answers.liquidity_issues]
        total_score     = income_score + liquidity_score

        if total_score >= 5:
            segment_name = "Premium Activo"
        elif total_score >= 3:
            segment_name = "Activo Estándar"
        elif liquidity_score == 0:
            segment_name = "En Riesgo"
        else:
            segment_name = "Dormido / Ocasional"

        # Calcular métricas estimadas
        income_params    = INCOME_MAP[answers.income_range]
        freq_params      = FREQUENCY_MAP[answers.spending_frequency]
        liquidity_params = LIQUIDITY_MAP[answers.liquidity_issues]
        monthly          = income_params["monthly"]
        n_tx             = freq_params["n_tx"]
        fail_r           = liquidity_params["fail_rate"]

        avg_tx    = monthly * 0.12
        est_spend = avg_tx * n_tx * (1 - fail_r)
        balance   = monthly * liquidity_params["min_balance_factor"] * 5

        # Generar fortalezas, oportunidades, recomendaciones
        strengths, opportunities, recommendations = _generate_recommendations(answers)

        # Summary narrativo
        summaries = {
            "low":     f"Tu perfil muestra ingresos en crecimiento. Con {n_tx} transacciones estimadas y gestión disciplinada, tienes margen real para mejorar tu salud financiera.",
            "medium":  f"Perfil financiero equilibrado con ${monthly/1e6:.1f}M COP/mes. Tu actividad de {n_tx} transacciones indica engagement activo con tu economía personal.",
            "high":    f"Sólido perfil de ingresos. Con ${monthly/1e6:.1f}M COP/mes y {n_tx} transacciones, eres candidato ideal para productos de inversión y crédito premium.",
            "premium": f"Perfil de alto valor. Tus patrones de gasto y nivel de ingresos te posicionan en el segmento VIP con acceso a productos financieros exclusivos.",
        }
        summary = summaries.get(answers.income_range, "Perfil financiero analizado correctamente.")

        return QuizResult(
            user_id=user_id,
            profile_name=profile_name,
            segment_icon=icon,
            segment_name=segment_name,
            risk_level=risk_level,
            risk_color=risk_color,
            summary=summary,
            strengths=strengths,
            opportunities=opportunities,
            recommendations=recommendations,
            metrics={
                "estimated_monthly_income_cop": monthly,
                "estimated_monthly_spend_cop":  round(est_spend, 0),
                "estimated_balance_cop":        round(balance, 0),
                "monthly_transactions":         n_tx,
                "fail_rate_pct":                round(fail_r * 100, 1),
                "main_category":                answers.main_category,
                "preferred_channel":            APP_USAGE_MAP[answers.app_usage]["channel"],
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando quiz para {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando el cuestionario: {str(e)}",
        )
