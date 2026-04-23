"""
agent/agent.py — Agente IA optimizado · FinTech NovaAI
═══════════════════════════════════════════════════════
PRIORIDAD:
  1. 🔥 Mistral-7B  — MISTRAL_BASE_URL  (fine-tuned Tesla T4)
  2. 🦙 LLaMA       — LLAMA_BASE_URL    (fallback opcional)
  3. 📋 Offline     — reglas determinísticas (siempre funciona)

FIX CRÍTICO:
  - Las env vars se leen en CALL TIME (no en import time).
    Así, exportar MISTRAL_BASE_URL después de arrancar uvicorn
    SÍ funciona sin reiniciar el proceso.
  - Timeout extendido a 60 s (local GPU puede ser lento).
  - Modo retornado siempre coherente: "mistral" | "llama" | "offline"
"""

import os
import json
import logging
import requests
import pandas as pd
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# ─── Timeouts ─────────────────────────────────────────────────────────────
CONNECT_TIMEOUT  = 5    # segundos para abrir conexión TCP
READ_TIMEOUT     = 90   # segundos esperando la respuesta (GPU local puede ser lenta)
HEALTH_TIMEOUT   = 4    # ping de health check

# ─── System prompt ────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un analista financiero senior especializado en fintech latinoamericana.
Tu misión: ayudar al usuario a entender su comportamiento financiero y tomar mejores decisiones.

REGLAS:
- Responde SIEMPRE en español.
- Máximo 200 palabras. Sé directo y accionable.
- Indica nivel de riesgo cuando aplique: BAJO / MEDIO / ALTO / CRÍTICO.
- Termina con una acción concreta que el usuario puede tomar HOY.
- Nunca inventes datos. Si no tienes suficiente info, dilo.

TONO: Profesional pero cercano, como un asesor financiero de confianza."""


# ══════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════════════════════

def _get_mistral_config() -> Tuple[str, str]:
    """
    Lee la URL y el modelo de Mistral en CALL TIME (no en import time).
    Esto permite cambiar MISTRAL_BASE_URL sin reiniciar el proceso.
    """
    url   = os.environ.get("MISTRAL_BASE_URL", "").strip().rstrip("/")
    model = os.environ.get("MISTRAL_MODEL", "mistral-fintech")
    return url, model


def _get_llama_config() -> Tuple[str, str]:
    """Lee la URL y el modelo de LLaMA en CALL TIME."""
    url   = os.environ.get("LLAMA_BASE_URL", "").strip().rstrip("/")
    model = os.environ.get("LLAMA_MODEL", "llama3.2:1b")
    return url, model


def check_llm_health(base_url: str, timeout: int = HEALTH_TIMEOUT) -> dict:
    """
    Verifica si un servidor LLM está disponible.
    Intenta GET /v1/models (OpenAI-compatible).
    Retorna dict con ok, latency_ms, models[].
    """
    if not base_url:
        return {"ok": False, "error": "URL vacía", "latency_ms": 0, "models": []}
    try:
        import time
        t0 = time.time()
        r  = requests.get(
            f"{base_url}/v1/models",
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        ms = int((time.time() - t0) * 1000)
        if r.status_code == 200:
            models = [m.get("id", "?") for m in r.json().get("data", [])]
            return {"ok": True, "latency_ms": ms, "models": models, "error": ""}
        return {"ok": False, "latency_ms": ms, "models": [], "error": f"HTTP {r.status_code}"}
    except requests.exceptions.ConnectionError as e:
        return {"ok": False, "latency_ms": 0, "models": [], "error": f"Conexión rechazada: {base_url}"}
    except requests.exceptions.Timeout:
        return {"ok": False, "latency_ms": 0, "models": [], "error": "Timeout de conexión"}
    except Exception as e:
        return {"ok": False, "latency_ms": 0, "models": [], "error": str(e)[:100]}


def build_user_context(user_row: pd.Series) -> str:
    """Construye el contexto financiero del usuario para el LLM."""
    cat_cols = [c for c in user_row.index if c.startswith("cat_")]
    cat_info = {
        c.replace("cat_", ""): f"${user_row.get(c, 0):,.0f} COP"
        for c in cat_cols
        if user_row.get(c, 0) > 0
    }
    uid = user_row.get("userId", getattr(user_row, "name", "N/A"))

    return f"""
PERFIL DEL USUARIO ({uid}):
  Nombre:   {user_row.get('name', 'N/A')} | Edad: {user_row.get('age', 'N/A')} años
  Ciudad:   {user_row.get('city', user_row.get('user_city', 'N/A'))}, {user_row.get('country', 'CO')}
  Segmento: {user_row.get('segment_icon', '')} {user_row.get('segment_name', 'N/A')} (cluster {user_row.get('cluster', '?')})

MÉTRICAS FINANCIERAS:
  Gasto total:      ${user_row.get('total_spent', 0):,.0f} COP
  Transacción avg:  ${user_row.get('avg_transaction', 0):,.0f} COP
  Balance actual:   ${user_row.get('current_balance', 0):,.0f} COP
  Balance avg:      ${user_row.get('avg_balance', 0):,.0f} COP
  Total recargado:  ${user_row.get('total_added', 0):,.0f} COP
  Total retirado:   ${user_row.get('total_withdrawn', 0):,.0f} COP
  Ratio gasto/rec:  {user_row.get('spend_vs_add_ratio', 0):.2f}

ACTIVIDAD:
  N° transacciones: {int(user_row.get('n_transactions', 0))}
  Exitosas:         {int(user_row.get('n_success', 0))} | Fallidas: {int(user_row.get('n_failed', 0))}
  Tasa de fallos:   {user_row.get('fail_ratio', 0) * 100:.1f}%
  Días activos:     {int(user_row.get('unique_days_active', 0))}
  Hora pico:        {user_row.get('peak_hour', '?')}:00
  Canal preferido:  {user_row.get('preferred_channel', 'N/A')}
  Dispositivo:      {user_row.get('preferred_device', 'N/A')}

GASTO POR CATEGORÍA:
{json.dumps(cat_info, ensure_ascii=False, indent=2)}

FLAGS DE RIESGO:
  Alto valor:        {'SÍ ✅' if user_row.get('is_high_value', 0) == 1 else 'No'}
  Balance bajo:      {'SÍ ⚠️' if user_row.get('is_low_balance', 0) == 1 else 'No'}
  Alto riesgo:       {'SÍ ⚠️' if user_row.get('is_high_risk', 0) == 1 else 'No'}
  Estrés financiero: {'SÍ 🚨' if user_row.get('financial_stress', 0) == 1 else 'No'}
  Dormido:           {'SÍ' if user_row.get('is_dormant', 0) == 1 else 'No'}
""".strip()


# ══════════════════════════════════════════════════════════════════════════
# CLIENTE LLM GENÉRICO (OpenAI-compatible)
# ══════════════════════════════════════════════════════════════════════════

def _call_openai_compatible(
    base_url:    str,
    model:       str,
    system:      str,
    user_prompt: str,
    history:     List[Dict],
    max_tokens:  int = 512,
    temperature: float = 0.3,
) -> str:
    """
    Llamada POST /v1/chat/completions con timeout extendido para GPU local.
    Lanza excepción si falla; el caller decide el fallback.
    """
    messages = [{"role": "system", "content": system}]
    # Incluir últimos 3 turnos (6 mensajes) del historial
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_prompt})

    response = requests.post(
        f"{base_url}/v1/chat/completions",
        json={
            "model":       model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "stream":      False,
        },
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        headers={"Content-Type": "application/json"},
    )

    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")

    content = response.json()["choices"][0]["message"]["content"]
    return content.strip()


# ══════════════════════════════════════════════════════════════════════════
# BACKENDS ESPECÍFICOS
# ══════════════════════════════════════════════════════════════════════════

def _try_mistral(question: str, user_context: str, history: List[Dict]) -> Optional[str]:
    """
    Intenta Mistral-7B fine-tuned.
    Lee MISTRAL_BASE_URL en call time → permite cambiarla sin reiniciar.
    """
    base_url, model = _get_mistral_config()
    if not base_url:
        logger.debug("MISTRAL_BASE_URL no configurada — saltando Mistral")
        return None

    prompt = f"Contexto del usuario:\n{user_context}\n\nPregunta: {question}"
    try:
        answer = _call_openai_compatible(
            base_url=base_url, model=model,
            system=SYSTEM_PROMPT, user_prompt=prompt,
            history=history,
        )
        logger.info(f"✅ Mistral respondió ({len(answer)} chars)")
        return answer
    except requests.exceptions.ConnectionError:
        logger.warning(f"⚠️  Mistral no disponible en {base_url} (ConnectionError)")
    except requests.exceptions.Timeout:
        logger.warning(f"⚠️  Mistral timeout después de {READ_TIMEOUT}s en {base_url}")
    except Exception as e:
        logger.warning(f"⚠️  Error Mistral: {e}")
    return None


def _try_llama(question: str, user_context: str, history: List[Dict]) -> Optional[str]:
    """
    Intenta LLaMA vía endpoint OpenAI-compatible.
    Lee LLAMA_BASE_URL en call time.
    """
    base_url, model = _get_llama_config()
    if not base_url:
        logger.debug("LLAMA_BASE_URL no configurada — saltando LLaMA")
        return None

    prompt = f"Contexto del usuario:\n{user_context}\n\nPregunta: {question}"
    try:
        answer = _call_openai_compatible(
            base_url=base_url, model=model,
            system=SYSTEM_PROMPT, user_prompt=prompt,
            history=history,
        )
        logger.info(f"✅ LLaMA respondió ({len(answer)} chars)")
        return answer
    except Exception as e:
        logger.warning(f"⚠️  Error LLaMA: {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════
# FALLBACK POR REGLAS — siempre disponible, < 1ms
# ══════════════════════════════════════════════════════════════════════════

def _rule_based_fallback(question: str, user_row: pd.Series) -> str:
    """
    Respuestas determinísticas de alta calidad.
    Sin dependencias externas. Latencia < 1ms.
    """
    q       = question.lower()
    name    = user_row.get("name", "usuario")
    spent   = user_row.get("total_spent", 0)
    balance = user_row.get("current_balance", 0)
    fail_r  = user_row.get("fail_ratio", 0) * 100
    seg     = user_row.get("segment_name", "N/A")
    seg_ico = user_row.get("segment_icon", "")

    # ── Gasto / categorías ─────────────────────────────────────────────
    if any(w in q for w in ["gast", "categor", "compr", "pag", "spend"]):
        cat_cols = [c for c in user_row.index if c.startswith("cat_")]
        cats = {c.replace("cat_", ""): user_row.get(c, 0) for c in cat_cols if user_row.get(c, 0) > 0}
        if cats:
            top     = max(cats, key=cats.get)
            top_val = cats[top]
            pct     = top_val / spent * 100 if spent > 0 else 0
            return (
                f"💳 **Gasto de {name}**\n\n"
                f"- Mayor categoría: **{top}** → ${top_val:,.0f} COP ({pct:.0f}% del total)\n"
                f"- Gasto total: **${spent:,.0f} COP**\n"
                f"- Promedio por transacción: **${user_row.get('avg_transaction', 0):,.0f} COP**\n\n"
                f"**Acción hoy:** Establece un presupuesto para *{top}* y activa una alerta "
                f"cuando superes el 80% de ese límite."
            )

    # ── Riesgo ─────────────────────────────────────────────────────────
    if any(w in q for w in ["riesgo", "peligro", "fallo", "fail", "stress", "estrés"]):
        stress = user_row.get("financial_stress", 0) == 1
        hi_risk = user_row.get("is_high_risk", 0) == 1
        lo_bal  = user_row.get("is_low_balance", 0) == 1
        level   = "CRÍTICO" if stress else ("ALTO" if hi_risk else ("MEDIO" if lo_bal or fail_r > 15 else "BAJO"))
        actions = {
            "CRÍTICO": "Contacta soporte inmediatamente y activa el límite de gasto diario.",
            "ALTO":    "Activa alertas de saldo y revisa pagos recurrentes esta semana.",
            "MEDIO":   "Monitorea tu tasa de fallos — si pasa del 25%, hay un problema de liquidez.",
            "BAJO":    "Perfil de riesgo saludable. Considera redirigir excedente hacia ahorro/inversión.",
        }
        flags = []
        if hi_risk:  flags.append("⚠️ Alta tasa de fallos")
        if stress:   flags.append("🚨 Estrés financiero combinado")
        if lo_bal:   flags.append("📉 Balance bajo — posible iliquidez")
        if user_row.get("is_dormant", 0): flags.append("😴 Usuario inactivo")
        if not flags: flags = ["✅ Sin señales críticas"]
        return (
            f"🔍 **Riesgo financiero: {level}**\n\n"
            + "\n".join(f"- {f}" for f in flags) +
            f"\n- Tasa de fallos: **{fail_r:.1f}%**\n"
            f"- Balance actual: **${balance:,.0f} COP**\n\n"
            f"**Acción hoy:** {actions[level]}"
        )

    # ── Balance / saldo ─────────────────────────────────────────────────
    if any(w in q for w in ["balance", "saldo", "dinero", "cuenta", "plata"]):
        avg_b   = user_row.get("avg_balance", 0)
        low     = user_row.get("is_low_balance", 0) == 1
        trend   = ("⬇️ por debajo" if balance < avg_b * 0.8
                   else "➡️ estable" if balance < avg_b * 1.2 else "⬆️ por encima")
        return (
            f"🏦 **Balance de {name}**\n\n"
            f"- Balance actual: **${balance:,.0f} COP**\n"
            f"- Promedio histórico: **${avg_b:,.0f} COP**\n"
            f"- Tendencia: {trend} del promedio\n"
            f"- Recargado: **${user_row.get('total_added', 0):,.0f} COP** | "
            f"Retirado: **${user_row.get('total_withdrawn', 0):,.0f} COP**\n\n"
            f"**Acción hoy:** {'Reduce gastos no esenciales urgentemente.' if low else 'Mantén un colchón del 20% de tu ingreso mensual en cuenta.'}"
        )

    # ── Patrón / comportamiento ─────────────────────────────────────────
    if any(w in q for w in ["patrón", "patron", "raro", "comportamiento", "habit", "inusual"]):
        return (
            f"📊 **Patrón de {name}**\n\n"
            f"- Hora pico: **{user_row.get('peak_hour', '?')}:00 hrs**\n"
            f"- Canal preferido: **{user_row.get('preferred_channel', 'N/A')}**\n"
            f"- Dispositivo: **{user_row.get('preferred_device', 'N/A')}**\n"
            f"- Días activos: **{int(user_row.get('unique_days_active', 0))}**\n"
            f"- Frecuencia: **{user_row.get('spending_frequency', 0):.1f} tx/día**\n\n"
            f"**Acción hoy:** Si ves transacciones fuera de las {user_row.get('peak_hour', '?')}:00 hrs que no reconoces, activa notificaciones de seguridad."
        )

    # ── Resumen completo ────────────────────────────────────────────────
    if any(w in q for w in ["resumen", "todo", "completo", "situación", "análisis", "analisis"]):
        n_tx = int(user_row.get("n_transactions", 0))
        return (
            f"📊 **Análisis completo de {name}**\n\n"
            f"- Segmento: **{seg_ico} {seg}**\n"
            f"- Gasto total: **${spent:,.0f} COP** en {n_tx} transacciones\n"
            f"- Balance actual: **${balance:,.0f} COP**\n"
            f"- Tasa de fallos: **{fail_r:.1f}%**\n"
            f"- Días activos: **{int(user_row.get('unique_days_active', 0))}**\n\n"
            f"**Acción hoy:** Revisa tus insights en el dashboard para "
            f"recomendaciones específicas basadas en tu perfil ML."
        )

    # ── Respuesta genérica ──────────────────────────────────────────────
    return (
        f"Hola {name} ({seg_ico} {seg}), gasto ${spent:,.0f} COP | balance ${balance:,.0f} COP.\n\n"
        f"Pregúntame sobre: gastos, riesgo, balance, patrones o pide un resumen completo.\n\n"
        f"💡 *Modo offline activo — configura `MISTRAL_BASE_URL` para análisis con IA generativa.*"
    )


# ══════════════════════════════════════════════════════════════════════════
# FUNCIÓN PÚBLICA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

def ask_agent(
    question: str,
    user_row:  pd.Series,
    history:   List[Dict] = None,
    api_key:   str = None,          # mantenido por compatibilidad, ya no se usa en main flow
) -> Tuple[str, List[Dict], str]:
    """
    Envía la pregunta al mejor agente disponible.

    Prioridad: Mistral-7B → LLaMA → Offline

    Returns:
        (respuesta, nuevo_historial, modo)
        modo: "mistral" | "llama" | "offline"
    """
    history      = history or []
    user_context = build_user_context(user_row)
    answer:  Optional[str] = None
    mode:    str = "offline"

    # 1️⃣  Mistral-7B (fine-tuned Tesla T4)
    answer = _try_mistral(question, user_context, history)
    if answer:
        mode = "mistral"

    # 2️⃣  LLaMA (fallback GPU secundario)
    if not answer:
        answer = _try_llama(question, user_context, history)
        if answer:
            mode = "llama"

    # 3️⃣  Reglas determinísticas (siempre funciona)
    if not answer:
        answer = _rule_based_fallback(question, user_row)
        mode   = "offline"
        mistral_url, _ = _get_mistral_config()
        if not mistral_url:
            answer += "\n\n> 💡 *Configura `MISTRAL_BASE_URL` en el sidebar para activar el LLM.*"

    new_history = history + [
        {"role": "user",      "content": question},
        {"role": "assistant", "content": answer},
    ]
    logger.info(f"Agent mode: {mode} | chars: {len(answer)}")
    return answer, new_history, mode