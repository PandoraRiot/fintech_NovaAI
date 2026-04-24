"""
insights/engine.py — Motor de Insights Automáticos
Genera 8 tipos de insights accionables con reglas determinísticas.
Latencia < 1ms. Sin dependencias externas. Siempre funciona.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import HIGH_VALUE_THRESHOLD, LOW_BALANCE_THRESHOLD, HIGH_FAIL_RATIO, DORMANT_TRANSACTIONS


def generate_portfolio_insights(gold: pd.DataFrame, top_anomalies: pd.DataFrame = None) -> List[Dict]:
    """
    Genera insights a nivel de portafolio (todos los usuarios).
    Retorna lista de diccionarios con: titulo, descripcion, accion, nivel, icono.
    """
    insights = []
    n = len(gold)

    # ── 1. Alta tasa de fallos en portafolio ──────────────────────────────
    high_fail_users = gold[gold["fail_ratio"] >= HIGH_FAIL_RATIO]
    pct_fail = len(high_fail_users) / n * 100
    if pct_fail > 20:
        insights.append({
            "titulo":      "🚨 Alta tasa de fallos sistémica",
            "descripcion": f"{len(high_fail_users):,} usuarios ({pct_fail:.1f}%) tienen >30% de transacciones fallidas.",
            "accion":      "Revisar flujos de pago — posible bug en pasarela o UX deficiente.",
            "nivel":       "crítico",
            "icono":       "🚨",
        })

    # ── 2. Estrés financiero combinado ────────────────────────────────────
    stress_users = gold[gold["financial_stress"] == 1]
    pct_stress = len(stress_users) / n * 100
    if pct_stress > 2:
        insights.append({
            "titulo":      "💸 Usuarios en estrés financiero",
            "descripcion": f"{len(stress_users):,} usuarios ({pct_stress:.1f}%) combinan bajo balance y alta tasa de fallos.",
            "accion":      "Activar programa de microcréditos o alertas de protección de saldo.",
            "nivel":       "alto",
            "icono":       "💸",
        })

    # ── 3. Usuarios dormidos ───────────────────────────────────────────────
    dormant = gold[gold["is_dormant"] == 1]
    pct_dormant = len(dormant) / n * 100
    if pct_dormant > 10:
        insights.append({
            "titulo":      "😴 Usuarios dormidos detectados",
            "descripcion": f"{len(dormant):,} usuarios ({pct_dormant:.1f}%) con ≤2 transacciones en el período.",
            "accion":      "Campaña de reactivación: cashback del 5% en primera transacción del mes.",
            "nivel":       "medio",
            "icono":       "😴",
        })

    # ── 4. Segmento Premium identificado ─────────────────────────────────
    premium = gold[gold["is_high_value"] == 1]
    if len(premium) > 0:
        avg_spent = premium["total_spent"].mean()
        insights.append({
            "titulo":      f"👑 {len(premium)} usuarios Premium identificados",
            "descripcion": f"Gasto promedio del segmento: ${avg_spent:,.0f} COP. Representan el {len(premium)/n*100:.1f}% del portafolio.",
            "accion":      "Lanzar programa VIP con beneficios exclusivos: 0% comisión en transferencias, seguro de viaje.",
            "nivel":       "oportunidad",
            "icono":       "👑",
        })

    # ── 5. Categoría de gasto dominante ──────────────────────────────────
    cat_cols = [c for c in gold.columns if c.startswith("cat_")]
    if cat_cols:
        cat_totals = gold[cat_cols].sum()
        top_cat = cat_totals.idxmax().replace("cat_", "")
        top_pct = cat_totals.max() / cat_totals.sum() * 100 if cat_totals.sum() > 0 else 0
        insights.append({
            "titulo":      f"🛒 Categoría dominante: {top_cat.upper()}",
            "descripcion": f"'{top_cat}' representa el {top_pct:.1f}% del gasto total del portafolio.",
            "accion":      f"Negociar alianzas con merchants de '{top_cat}' para cashback exclusivo — máximo retorno de inversión en marketing.",
            "nivel":       "oportunidad",
            "icono":       "🛒",
        })

    # ── 6. Hora pico del sistema ──────────────────────────────────────────
    if "peak_hour" in gold.columns:
        peak = int(gold["peak_hour"].mode()[0])
        insights.append({
            "titulo":      f"⏰ Hora pico del sistema: {peak:02d}:00",
            "descripcion": f"La mayoría de usuarios realizan transacciones alrededor de las {peak:02d}:00 hrs.",
            "accion":      f"Programar mantenimientos entre 02:00–05:00 hrs. Escalar infraestructura antes de las {peak:02d}:00.",
            "nivel":       "info",
            "icono":       "⏰",
        })

    # ── 7. Anomalías detectadas ───────────────────────────────────────────
    if top_anomalies is not None and len(top_anomalies) > 0:
        n_anom = len(top_anomalies)
        avg_amount = top_anomalies["amount"].mean()
        insights.append({
            "titulo":      f"🔍 {n_anom} transacciones anómalas detectadas",
            "descripcion": f"Monto promedio de anomalías: ${avg_amount:,.0f} COP. Isolation Forest detectó patrones inusuales.",
            "accion":      "Revisar manualmente el top 10 de mayor anomaly score. Enviar notificación push a los usuarios afectados.",
            "nivel":       "alto",
            "icono":       "🔍",
        })

    # ── 8. Canal principal ────────────────────────────────────────────────
    if "preferred_channel" in gold.columns:
        top_channel = gold["preferred_channel"].mode()[0]
        pct_channel = (gold["preferred_channel"] == top_channel).sum() / n * 100
        insights.append({
            "titulo":      f"📱 Canal preferido: {top_channel.upper()}",
            "descripcion": f"{pct_channel:.1f}% de usuarios prefieren el canal '{top_channel}'.",
            "accion":      f"Priorizar optimizaciones de UX y nuevas features en el canal '{top_channel}' para máximo impacto.",
            "nivel":       "info",
            "icono":       "📱",
        })

    return insights


def generate_user_insights(user_row: pd.Series) -> List[Dict]:
    """Genera insights personalizados para un usuario específico."""
    insights = []

    # Riesgo financiero
    if user_row.get("financial_stress", 0) == 1:
        insights.append({
            "titulo": "⚠️ Estrés financiero detectado",
            "descripcion": f"Balance crítico (${user_row.get('current_balance', 0):,.0f} COP) combinado con {user_row.get('fail_ratio', 0)*100:.0f}% de fallos.",
            "accion": "Considerar ajuste de límites de gasto o activar alerta de saldo mínimo.",
            "nivel": "crítico",
        })

    # Usuario premium
    if user_row.get("is_high_value", 0) == 1:
        insights.append({
            "titulo": "👑 Usuario de alto valor",
            "descripcion": f"Gasto total de ${user_row.get('total_spent', 0):,.0f} COP lo ubica en el segmento Premium.",
            "accion": "Ofrecer acceso al programa VIP con beneficios exclusivos.",
            "nivel": "oportunidad",
        })

    # Usuario dormido
    if user_row.get("is_dormant", 0) == 1:
        insights.append({
            "titulo": "😴 Usuario dormido",
            "descripcion": f"Solo {user_row.get('n_transactions', 0):.0f} transacciones registradas.",
            "accion": "Enviar notificación personalizada con incentivo de reactivación.",
            "nivel": "medio",
        })

    # Categoría dominante del usuario
    cat_cols = [c for c in user_row.index if c.startswith("cat_")]
    if cat_cols:
        cat_values = {c.replace("cat_", ""): user_row.get(c, 0) for c in cat_cols}
        top_cat = max(cat_values, key=cat_values.get)
        top_val = cat_values[top_cat]
        if top_val > 0:
            insights.append({
                "titulo": f"🛒 Gasto principal en {top_cat}",
                "descripcion": f"Ha gastado ${top_val:,.0f} COP en '{top_cat}'.",
                "accion": f"Ofrecer cashback específico de '{top_cat}' para fidelizar este comportamiento.",
                "nivel": "info",
            })

    return insights
