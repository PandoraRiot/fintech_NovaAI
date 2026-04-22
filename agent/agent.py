"""
agent/agent.py — Agente IA con soporte multi-modelo + fallback por reglas
════════════════════════════════════════════════════════════════════════════

Prioridad de inferencia:
  1. 🦙 LLaMA 3.2 1B  via OpenAI-compatible API (vLLM/Ollama)
     → Configurar: LLAMA_BASE_URL=http://tu-cluster:8080
     → Configurar: LLAMA_MODEL=llama3.2:1b (o el nombre del modelo en tu servidor)

  2. 🤖 Claude API (Anthropic)
     → Configurar: ANTHROPIC_API_KEY=sk-ant-...

  3. 📋 Modo offline — reglas determinísticas
     → Siempre disponible, sin dependencias externas
     → Respuestas accionables y consistentes

El agente NUNCA alucina: si no tiene datos, lo dice explícitamente.
"""
import os
import json
import logging
import requests
import pandas as pd
from typing import List, Dict, Tuple
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# ── Configuración del agente ──────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un analista financiero senior especializado en fintech latinoamericana.
Tu misión: ayudar al usuario a entender su comportamiento financiero y tomar mejores decisiones.

REGLAS ABSOLUTAS:
- Responde SIEMPRE en español
- Máximo 200 palabras por respuesta
- Sé directo y accionable — no describas solo, RECOMIENDA
- Indica siempre el nivel de riesgo cuando sea relevante: BAJO / MEDIO / ALTO / CRÍTICO
- Termina SIEMPRE con una acción concreta que el usuario puede tomar HOY
- Si los datos no son suficientes para responder con certeza, dilo honestamente
- Nunca inventes datos o estadísticas que no estén en el contexto

TONO: Profesional pero cercano. Como un asesor financiero de confianza en una reunión one-on-one."""

REQUEST_TIMEOUT = 10


def build_user_context(user_row: pd.Series) -> str:
    """Construye el contexto financiero del usuario para el prompt."""
    cat_cols = [c for c in user_row.index if c.startswith("cat_")]
    cat_info = {
        c.replace("cat_", ""): f"${user_row.get(c, 0):,.0f} COP"
        for c in cat_cols
        if user_row.get(c, 0) > 0
    }

    return f"""
PERFIL DEL USUARIO:
- Nombre: {user_row.get('name', 'N/A')} | Edad: {user_row.get('age', 'N/A')} años
- Ciudad: {user_row.get('city', 'N/A')}, {user_row.get('country', 'N/A')}
- Segmento ML asignado: {user_row.get('segment_icon', '')} {user_row.get('segment_name', 'N/A')}

MÉTRICAS FINANCIERAS:
- Gasto total del período: ${user_row.get('total_spent', 0):,.0f} COP
- Transacción promedio: ${user_row.get('avg_transaction', 0):,.0f} COP
- Transacción máxima: ${user_row.get('max_transaction', 0):,.0f} COP
- Balance actual: ${user_row.get('current_balance', 0):,.0f} COP
- Balance promedio histórico: ${user_row.get('avg_balance', 0):,.0f} COP

ACTIVIDAD:
- Total transacciones: {user_row.get('n_transactions', 0):.0f}
- Exitosas: {user_row.get('n_success', 0):.0f} | Fallidas: {user_row.get('n_failed', 0):.0f}
- Tasa de fallos: {user_row.get('fail_ratio', 0)*100:.1f}%
- Días activos en el período: {user_row.get('unique_days_active', 0):.0f}
- Hora pico de actividad: {user_row.get('peak_hour', 'N/A')}:00 hrs
- Canal preferido: {user_row.get('preferred_channel', 'N/A')}

GASTO POR CATEGORÍA:
{json.dumps(cat_info, ensure_ascii=False, indent=2)}

SEÑALES DE RIESGO:
- Usuario Premium (alto valor): {'SÍ' if user_row.get('is_high_value', 0) == 1 else 'NO'}
- Balance crítico (<$100k COP): {'SÍ ⚠️' if user_row.get('is_low_balance', 0) == 1 else 'NO'}
- Alta tasa de fallos (>30%): {'SÍ ⚠️' if user_row.get('is_high_risk', 0) == 1 else 'NO'}
- Estrés financiero combinado: {'SÍ 🚨' if user_row.get('financial_stress', 0) == 1 else 'NO'}
- Usuario dormido (≤2 tx): {'SÍ' if user_row.get('is_dormant', 0) == 1 else 'NO'}
""".strip()


# ══════════════════════════════════════════════════════════════════════════
# 1. LLAMA 3.2 via OpenAI-compatible endpoint (vLLM / Ollama)
# ══════════════════════════════════════════════════════════════════════════

def _try_llama(question: str, user_context: str, history: List[Dict]) -> str | None:
    """
    Intenta inferencia con LLaMA 3.2 vía endpoint OpenAI-compatible.
    Compatible con: Ollama (http://localhost:11434), vLLM, LM Studio, etc.

    Configurar en .env:
      LLAMA_BASE_URL=http://tu-cluster:8080
      LLAMA_MODEL=llama3.2:1b
    """
    base_url = os.environ.get("LLAMA_BASE_URL", "").rstrip("/")
    if not base_url:
        return None

    model = os.environ.get("LLAMA_MODEL", "llama3.2:1b")

    # Construir mensajes en formato OpenAI Chat
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history[-6:]:  # últimos 3 turnos para no saturar el contexto
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({
        "role": "user",
        "content": f"{user_context}\n\nPREGUNTA: {question}"
    })

    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model":       model,
                "messages":    messages,
                "max_tokens":  400,
                "temperature": 0.3,   # bajo para respuestas más consistentes
                "stream":      False,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ LLaMA respondió ({len(text)} chars)")
            return text
        else:
            logger.warning(f"LLaMA HTTP {response.status_code}: {response.text[:200]}")
    except requests.exceptions.ConnectionError:
        logger.warning(f"LLaMA no disponible en {base_url}")
    except Exception as e:
        logger.warning(f"Error en LLaMA: {e}")

    return None


# ══════════════════════════════════════════════════════════════════════════
# 2. CLAUDE API (Anthropic) — fallback secundario
# ══════════════════════════════════════════════════════════════════════════

def _try_claude(question: str, user_context: str, history: List[Dict], api_key: str) -> str | None:
    """Intenta inferencia con Claude API de Anthropic."""
    if not api_key:
        return None

    messages = []
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({
        "role": "user",
        "content": f"{user_context}\n\nPREGUNTA DEL USUARIO: {question}"
    })

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":          api_key,
                "anthropic-version":  "2023-06-01",
                "content-type":       "application/json",
            },
            json={
                "model":      "claude-sonnet-4-20250514",
                "max_tokens": 400,
                "system":     SYSTEM_PROMPT,
                "messages":   messages,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            text = response.json()["content"][0]["text"].strip()
            logger.info(f"✅ Claude respondió ({len(text)} chars)")
            return text
        else:
            logger.warning(f"Claude HTTP {response.status_code}")
    except Exception as e:
        logger.warning(f"Error en Claude API: {e}")

    return None


# ══════════════════════════════════════════════════════════════════════════
# 3. FALLBACK POR REGLAS — siempre disponible
# ══════════════════════════════════════════════════════════════════════════

def _rule_based_fallback(question: str, user_row: pd.Series) -> str:
    """
    Respuestas determinísticas de alta calidad.
    Mapea patrones de pregunta → respuesta accionable.
    Latencia: < 1ms. Sin dependencias externas.
    """
    q = question.lower()

    # — Gasto / categorías ─────────────────────────────────────────────────
    if any(w in q for w in ["gast", "spend", "categor", "compr", "pag"]):
        cat_cols = [c for c in user_row.index if c.startswith("cat_")]
        cat_values = {c.replace("cat_", ""): user_row.get(c, 0) for c in cat_cols if user_row.get(c, 0) > 0}
        if cat_values:
            top = max(cat_values, key=cat_values.get)
            top_val = cat_values[top]
            total_spend = user_row.get("total_spent", 0)
            pct = top_val / total_spend * 100 if total_spend > 0 else 0
            return (
                f"Tu mayor gasto está en **{top}** con ${top_val:,.0f} COP "
                f"({pct:.0f}% de tu gasto total de ${total_spend:,.0f} COP). "
                f"Promedio por transacción: ${user_row.get('avg_transaction', 0):,.0f} COP.\n\n"
                f"**Acción para hoy:** Establece un presupuesto mensual para '{top}' "
                f"y usa una app de seguimiento para monitorear en tiempo real."
            )

    # — Riesgo / fallos ────────────────────────────────────────────────────
    if any(w in q for w in ["riesgo", "risk", "peligro", "fallo", "fail", "probl"]):
        fail_r   = user_row.get("fail_ratio", 0) * 100
        balance  = user_row.get("current_balance", 0)
        stress   = user_row.get("financial_stress", 0) == 1
        level = "CRÍTICO" if stress else ("ALTO" if fail_r > 30 else ("MEDIO" if fail_r > 15 else "BAJO"))
        action = {
            "CRÍTICO": "Contacta soporte ahora y activa el límite de gasto diario urgentemente.",
            "ALTO":    "Activa alertas de saldo y revisa tus pagos recurrentes esta semana.",
            "MEDIO":   "Monitorea tu tasa de fallos — si supera el 25%, hay un problema de liquidez.",
            "BAJO":    "Tu perfil de riesgo es saludable. Considera redirigir el ahorro hacia inversión.",
        }[level]
        return (
            f"**Nivel de riesgo financiero: {level}**\n"
            f"- Tasa de transacciones fallidas: {fail_r:.1f}%\n"
            f"- Balance actual: ${balance:,.0f} COP\n"
            f"- Estrés financiero combinado: {'Sí ⚠️' if stress else 'No ✅'}\n\n"
            f"**Acción para hoy:** {action}"
        )

    # — Balance / saldo ────────────────────────────────────────────────────
    if any(w in q for w in ["balance", "saldo", "dinero", "cuenta", "plata"]):
        balance = user_row.get("current_balance", 0)
        avg_b   = user_row.get("avg_balance", 0)
        low     = user_row.get("is_low_balance", 0) == 1
        trend   = "⬇️ por debajo" if balance < avg_b * 0.8 else ("➡️ estable" if balance < avg_b * 1.2 else "⬆️ por encima")
        action = (
            "Reduce gastos no esenciales esta semana y transfiere fondos urgentemente."
            if low else
            "Considera dejar un colchón de seguridad del 20% de tu ingreso mensual en cuenta."
        )
        return (
            f"**Balance actual:** ${balance:,.0f} COP\n"
            f"- Promedio histórico: ${avg_b:,.0f} COP\n"
            f"- Tendencia: {trend} del promedio\n"
            f"- Estado: {'⚠️ Balance crítico' if low else '✅ Balance saludable'}\n\n"
            f"**Acción para hoy:** {action}"
        )

    # — Patrones / comportamiento ──────────────────────────────────────────
    if any(w in q for w in ["patrón", "patron", "raro", "inusual", "comportamiento", "habit"]):
        peak    = user_row.get("peak_hour", "?")
        channel = user_row.get("preferred_channel", "app")
        weekend = user_row.get("weekend_transactions", 0)
        days    = user_row.get("unique_days_active", 0)
        return (
            f"**Tu patrón de comportamiento financiero:**\n"
            f"- Hora pico: **{peak}:00 hrs** (mayoría de tus transacciones)\n"
            f"- Canal preferido: **{channel}**\n"
            f"- Transacciones en fin de semana: {weekend:.0f}\n"
            f"- Días activos en el período: {days:.0f}\n\n"
            f"**Acción para hoy:** Si ves transacciones fuera de las {peak}:00 hrs "
            f"que no reconoces, activa notificaciones de seguridad en tu app."
        )

    # — Resumen general ────────────────────────────────────────────────────
    if any(w in q for w in ["resumen", "todo", "completo", "situación", "analisis"]):
        name    = user_row.get("name", "usuario")
        segment = user_row.get("segment_name", "N/A")
        spend   = user_row.get("total_spent", 0)
        balance = user_row.get("current_balance", 0)
        fail_r  = user_row.get("fail_ratio", 0) * 100
        n_tx    = user_row.get("n_transactions", 0)
        return (
            f"**Análisis completo de {name}:**\n\n"
            f"📊 **Segmento:** {segment}\n"
            f"💰 **Gasto total:** ${spend:,.0f} COP en {n_tx:.0f} transacciones\n"
            f"🏦 **Balance actual:** ${balance:,.0f} COP\n"
            f"❌ **Tasa de fallos:** {fail_r:.1f}%\n\n"
            f"**Acción para hoy:** Revisa la sección de Insights en el dashboard "
            f"para ver recomendaciones específicas basadas en tu perfil ML."
        )

    # — Respuesta genérica ─────────────────────────────────────────────────
    name    = user_row.get("name", "usuario")
    segment = user_row.get("segment_name", "N/A")
    spend   = user_row.get("total_spent", 0)
    balance = user_row.get("current_balance", 0)
    return (
        f"Hola {name}, basado en tu perfil **{segment}**:\n"
        f"Gasto total ${spend:,.0f} COP | Balance ${balance:,.0f} COP.\n\n"
        f"Pregúntame sobre: gastos, riesgo, balance, patrones, o pide un resumen completo.\n\n"
        f"**Acción para hoy:** Consulta la sección Insights en el dashboard para "
        f"recomendaciones personalizadas de tu perfil ML."
    )


# ══════════════════════════════════════════════════════════════════════════
# FUNCIÓN PÚBLICA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

def ask_agent(
    question: str,
    user_row: pd.Series,
    history: List[Dict] = None,
    api_key: str = None,
) -> Tuple[str, List[Dict], str]:
    """
    Envía la pregunta al mejor agente disponible.

    Prioridad: LLaMA 3.2 → Claude → Offline

    Returns:
        (respuesta_texto, nuevo_historial, modo_usado)
        modo_usado: "llama" | "claude" | "offline"
    """
    history     = history or []
    user_context = build_user_context(user_row)
    answer       = None
    mode         = "offline"

    # 1️⃣  Intentar LLaMA 3.2 (cluster asignado)
    answer = _try_llama(question, user_context, history)
    if answer:
        mode = "llama"

    # 2️⃣  Intentar Claude API
    if not answer:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        answer = _try_claude(question, user_context, history, key)
        if answer:
            mode = "claude"

    # 3️⃣  Fallback por reglas (siempre funciona)
    if not answer:
        answer = _rule_based_fallback(question, user_row)
        mode   = "offline"
        answer += "\n\n*[Modo offline — configura LLAMA_BASE_URL o ANTHROPIC_API_KEY para análisis más profundo]*"

    # Actualizar historial
    new_history = history + [
        {"role": "user",      "content": question},
        {"role": "assistant", "content": answer},
    ]

    logger.info(f"Agente respondió en modo '{mode}' ({len(answer)} chars)")
    return answer, new_history, mode
