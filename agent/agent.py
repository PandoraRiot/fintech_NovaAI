"""
<<<<<<< HEAD
 HEAD
agent/agent.py — Agente IA financiero · Producción
════════════════════════════════════════════════════════════════════════════

Arquitectura de inferencia (prioridad descendente):
  1. 🦙 LLaMA 3.2   — vLLM / Ollama (OpenAI-compatible)
  2. 🤖 Mistral 7B  — local, Transformers + 4-bit (mistral_local.py)
  3. 🌐 Claude API  — Anthropic (fallback de red)
  4. 📋 Reglas      — determinístico, sin dependencias, latencia ~0ms

Características de producción incluidas:
  ✦ Circuit Breaker por endpoint (evita cascadas de timeout)
  ✦ Retry con exponential backoff + jitter
  ✦ Cache LRU de respuestas (evita re-inferir preguntas idénticas)
  ✦ Validador de calidad de respuesta (descarta alucinaciones obvias)
  ✦ Fallback por reglas completo (4 categorías de pregunta × 4 segmentos)
  ✦ Prompt engineering con few-shot + chain-of-thought condensado
  ✦ Detección de idioma con wordlists extendidas
  ✦ Score de riesgo numérico (0–100)
  ✦ Post-procesamiento del output (limpieza de artefactos LLM)
  ✦ Logging estructurado con request_id trazable
  ✦ Config centralizada vía dataclass + variables de entorno
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import sys
import time
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple
=======
agent/agent.py — Agente IA optimizado · FinTech NovaAI
═══════════════════════════════════════════════════════
PRIORIDAD:
  1. 🔥 Mistral-7B  — MISTRAL_BASE_URL  (fine-tuned Tesla T4)
  2. 🦙 LLaMA       — LLAMA_BASE_URL    (fallback opcional)
  3. 📋 Offline     — reglas determinísticas (siempre funciona)
=======
agent/agent.py — Agente IA financiero · Producción
════════════════════════════════════════════════════════════════════════════
>>>>>>> b8a43b0 (chore: remove data folder from repo)

Arquitectura de inferencia (prioridad descendente):
  1. 🦙 LLaMA 3.2   — vLLM / Ollama (OpenAI-compatible)
  2. 🤖 Mistral 7B  — local, Transformers + 4-bit (mistral_local.py)
  3. 🌐 Claude API  — Anthropic (fallback de red)
  4. 📋 Reglas      — determinístico, sin dependencias, latencia ~0ms

Características de producción incluidas:
  ✦ Circuit Breaker por endpoint (evita cascadas de timeout)
  ✦ Retry con exponential backoff + jitter
  ✦ Cache LRU de respuestas (evita re-inferir preguntas idénticas)
  ✦ Validador de calidad de respuesta (descarta alucinaciones obvias)
  ✦ Fallback por reglas completo (4 categorías de pregunta × 4 segmentos)
  ✦ Prompt engineering con few-shot + chain-of-thought condensado
  ✦ Detección de idioma con wordlists extendidas
  ✦ Score de riesgo numérico (0–100)
  ✦ Post-procesamiento del output (limpieza de artefactos LLM)
  ✦ Logging estructurado con request_id trazable
  ✦ Config centralizada vía dataclass + variables de entorno
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import sys
import time
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
<<<<<<< HEAD
from typing import List, Dict, Tuple, Optional
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)

import pandas as pd
import requests

<<<<<<< HEAD
# ── sys.path primero, ANTES de imports locales ────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.mistral_local import generate_response
# ──────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────

=======
import requests

# ── sys.path primero, ANTES de imports locales ────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.mistral_local import generate_response
# ──────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────

>>>>>>> b8a43b0 (chore: remove data folder from repo)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
<<<<<<< HEAD


# ══════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class AgentConfig:
    """Config centralizada. Los valores pueden venir de .env vía os.environ."""

    # ── Endpoints ──────────────────────────────────────────────────────────
    llama_base_url: str       = field(default_factory=lambda: os.environ.get("LLAMA_BASE_URL", "").rstrip("/"))
    llama_model: str          = field(default_factory=lambda: os.environ.get("LLAMA_MODEL", "llama3.2:1b"))
    anthropic_api_key: str    = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    claude_model: str         = "claude-sonnet-4-20250514"

    # ── Timeouts & retries ──────────────────────────────────────────────────
    request_timeout: int      = 12
    max_retries: int          = 2
    retry_base_delay: float   = 0.4   # seg — se duplica en cada intento + jitter

    # ── Circuit Breaker ────────────────────────────────────────────────────
    cb_failure_threshold: int = 3     # fallos consecutivos para abrir el circuito
    cb_cooldown_secs: int     = 60    # seg antes de intentar de nuevo

    # ── Generación ─────────────────────────────────────────────────────────
    max_tokens: int           = 450
    temperature: float        = 0.25
    max_history_turns: int    = 6     # turnos anteriores incluidos en el contexto

    # ── Cache ──────────────────────────────────────────────────────────────
    cache_max_size: int       = 256   # entradas LRU máximas


CFG = AgentConfig()


# ══════════════════════════════════════════════════════════════════════════
# PROMPT ENGINEERING
# ══════════════════════════════════════════════════════════════════════════

# Prompt del sistema: instrucciones + formato obligatorio + few-shot compacto
SYSTEM_PROMPT = """\
Eres un analista financiero senior especializado en fintech latinoamericana.
Tu misión: ayudar al usuario a entender su comportamiento financiero y tomar mejores decisiones.

══ REGLAS ABSOLUTAS ══
• Responde en el idioma de la pregunta (español o inglés).
• Máximo 220 palabras.
• Sé directo y accionable — no describas solo, RECOMIENDA.
• Nunca inventes datos o estadísticas que no estén en el contexto provisto.
• Si los datos son insuficientes, admítelo honestamente.

══ FORMATO OBLIGATORIO (usa siempre esta estructura) ══
🔍 DIAGNÓSTICO
<una oración con el hallazgo principal>

⚠️ NIVEL DE RIESGO: <BAJO | MEDIO | ALTO | CRÍTICO>
<una oración que justifique el nivel>
=======
# ─── Timeouts ─────────────────────────────────────────────────────────────
CONNECT_TIMEOUT  = 5    # segundos para abrir conexión TCP
READ_TIMEOUT     = 90   # segundos esperando la respuesta (GPU local puede ser lenta)
HEALTH_TIMEOUT   = 4    # ping de health check
=======
>>>>>>> b8a43b0 (chore: remove data folder from repo)


# ══════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class AgentConfig:
    """Config centralizada. Los valores pueden venir de .env vía os.environ."""

    # ── Endpoints ──────────────────────────────────────────────────────────
    llama_base_url: str       = field(default_factory=lambda: os.environ.get("LLAMA_BASE_URL", "").rstrip("/"))
    llama_model: str          = field(default_factory=lambda: os.environ.get("LLAMA_MODEL", "llama3.2:1b"))
    anthropic_api_key: str    = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    claude_model: str         = "claude-sonnet-4-20250514"

    # ── Timeouts & retries ──────────────────────────────────────────────────
    request_timeout: int      = 12
    max_retries: int          = 2
    retry_base_delay: float   = 0.4   # seg — se duplica en cada intento + jitter

    # ── Circuit Breaker ────────────────────────────────────────────────────
    cb_failure_threshold: int = 3     # fallos consecutivos para abrir el circuito
    cb_cooldown_secs: int     = 60    # seg antes de intentar de nuevo

    # ── Generación ─────────────────────────────────────────────────────────
    max_tokens: int           = 450
    temperature: float        = 0.25
    max_history_turns: int    = 6     # turnos anteriores incluidos en el contexto

    # ── Cache ──────────────────────────────────────────────────────────────
    cache_max_size: int       = 256   # entradas LRU máximas


CFG = AgentConfig()


# ══════════════════════════════════════════════════════════════════════════
# PROMPT ENGINEERING
# ══════════════════════════════════════════════════════════════════════════

# Prompt del sistema: instrucciones + formato obligatorio + few-shot compacto
SYSTEM_PROMPT = """\
Eres un analista financiero senior especializado en fintech latinoamericana.
Tu misión: ayudar al usuario a entender su comportamiento financiero y tomar mejores decisiones.

══ REGLAS ABSOLUTAS ══
• Responde en el idioma de la pregunta (español o inglés).
• Máximo 220 palabras.
• Sé directo y accionable — no describas solo, RECOMIENDA.
• Nunca inventes datos o estadísticas que no estén en el contexto provisto.
• Si los datos son insuficientes, admítelo honestamente.

══ FORMATO OBLIGATORIO (usa siempre esta estructura) ══
🔍 DIAGNÓSTICO
<una oración con el hallazgo principal>

⚠️ NIVEL DE RIESGO: <BAJO | MEDIO | ALTO | CRÍTICO>
<una oración que justifique el nivel>

💡 RECOMENDACIÓN
<2-3 acciones concretas priorizadas>

✅ ACCIÓN PARA HOY
<una sola acción inmediata y específica>

══ FEW-SHOT EXAMPLES ══

[EJEMPLO 1 — riesgo CRÍTICO]
PREGUNTA: ¿Estoy en riesgo financiero?
RESPUESTA:
🔍 DIAGNÓSTICO
Tu tasa de fallos del 25% y balance de $50.000 COP indican estrés financiero activo.
⚠️ NIVEL DE RIESGO: CRÍTICO
Combinas bajo balance, alta tasa de fallos y actividad nocturna, patrón típico de sobreendeudamiento.
💡 RECOMENDACIÓN
1. Pausa compras no esenciales los próximos 7 días.
2. Renegocia si tienes deudas pendientes.
3. Activa alertas de saldo mínimo en la app.
✅ ACCIÓN PARA HOY
Revisa los 5 últimos gastos y cancela al menos uno recurrente que no necesitas.

[EJEMPLO 2 — riesgo BAJO]
PREGUNTA: ¿Cómo está mi balance?
RESPUESTA:
🔍 DIAGNÓSTICO
Tu balance actual de $1.200.000 COP supera tu promedio histórico de $900.000, señal positiva.
⚠️ NIVEL DE RIESGO: BAJO
Tienes liquidez saludable y una tasa de fallos del 2%.
💡 RECOMENDACIÓN
1. Considera mover el excedente a un ahorro de corto plazo.
2. Mantén al menos $400.000 como reserva de emergencia.
✅ ACCIÓN PARA HOY
Transfiere $200.000 a una cuenta de ahorro o CDT de bajo riesgo.\
"""

# Instrucción de idioma inyectada dinámicamente
_LANG_INSTRUCTIONS = {
    "es": "Responde completamente en español. No uses inglés bajo ninguna circunstancia.",
    "en": "Respond entirely in English. Do not use Spanish under any circumstances.",
}


# ══════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ══════════════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """
    Patrón Circuit Breaker para endpoints HTTP.

    CLOSED  → llamadas normales.
    OPEN    → bloquea llamadas por `cooldown_secs` tras `failure_threshold` fallos.
    HALF-OPEN → permite 1 intento de prueba al expirar el cooldown.
    """

    def __init__(self, name: str, failure_threshold: int, cooldown_secs: int) -> None:
        self.name = name
        self._threshold = failure_threshold
        self._cooldown = cooldown_secs
        self._failures = 0
        self._opened_at: Optional[float] = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at > self._cooldown:
            log.info(f"[CB:{self.name}] Cooldown expirado → HALF-OPEN, intentando de nuevo…")
            self._opened_at = None  # permite un intento de prueba
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = time.monotonic()
            log.warning(
                f"[CB:{self.name}] ABIERTO tras {self._failures} fallos. "
                f"Cooldown: {self._cooldown}s."
            )


_cb_llama  = CircuitBreaker("LLaMA",  CFG.cb_failure_threshold, CFG.cb_cooldown_secs)
_cb_claude = CircuitBreaker("Claude", CFG.cb_failure_threshold, CFG.cb_cooldown_secs)


# ══════════════════════════════════════════════════════════════════════════
# CACHE DE RESPUESTAS (LRU)
# ══════════════════════════════════════════════════════════════════════════

def _cache_key(user_context: str, question: str) -> str:
    """Hash SHA-256 truncado para usar como clave de cache."""
    raw = f"{user_context}||{question.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


_response_cache: Dict[str, str] = {}   # se limita con _evict_cache()
_cache_order: List[str] = []           # FIFO para LRU manual (sin dependencias extra)


def _cache_get(key: str) -> Optional[str]:
    return _response_cache.get(key)


def _cache_set(key: str, value: str) -> None:
    if key in _response_cache:
        return
    if len(_cache_order) >= CFG.cache_max_size:
        oldest = _cache_order.pop(0)
        _response_cache.pop(oldest, None)
    _response_cache[key] = value
    _cache_order.append(key)


# ══════════════════════════════════════════════════════════════════════════
# DETECCIÓN DE IDIOMA
# ══════════════════════════════════════════════════════════════════════════

_ES_WORDS = {
    "qué", "cómo", "cuál", "cuánto", "cuándo", "dónde", "quién",
    "estoy", "tengo", "gasto", "gasté", "saldo", "balance", "riesgo",
    "dinero", "deuda", "ahorro", "cuenta", "banco", "pago", "cobro",
    "hola", "dame", "dime", "ayuda", "resumen", "análisis", "situación",
    "financiero", "financiera", "transacción", "movimiento",
}

_EN_WORDS = {
    "what", "how", "which", "when", "where", "who", "my", "am", "is",
    "balance", "risk", "spend", "spent", "money", "debt", "saving",
    "account", "bank", "payment", "transaction", "summary", "analysis",
    "financial", "help", "show", "tell",
}


def detect_language(text: str) -> str:
    """Detecta idioma por intersección con wordlists. Default: 'es'."""
    words = set(text.lower().split())
    score_es = len(words & _ES_WORDS)
    score_en = len(words & _EN_WORDS)
    return "en" if score_en > score_es else "es"


# ══════════════════════════════════════════════════════════════════════════
# RIESGO FINANCIERO
# ══════════════════════════════════════════════════════════════════════════

def compute_risk_score(user_row: pd.Series) -> Tuple[int, str]:
    """
<<<<<<< HEAD
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
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)

💡 RECOMENDACIÓN
<2-3 acciones concretas priorizadas>

✅ ACCIÓN PARA HOY
<una sola acción inmediata y específica>

══ FEW-SHOT EXAMPLES ══

[EJEMPLO 1 — riesgo CRÍTICO]
PREGUNTA: ¿Estoy en riesgo financiero?
RESPUESTA:
🔍 DIAGNÓSTICO
Tu tasa de fallos del 25% y balance de $50.000 COP indican estrés financiero activo.
⚠️ NIVEL DE RIESGO: CRÍTICO
Combinas bajo balance, alta tasa de fallos y actividad nocturna, patrón típico de sobreendeudamiento.
💡 RECOMENDACIÓN
1. Pausa compras no esenciales los próximos 7 días.
2. Renegocia si tienes deudas pendientes.
3. Activa alertas de saldo mínimo en la app.
✅ ACCIÓN PARA HOY
Revisa los 5 últimos gastos y cancela al menos uno recurrente que no necesitas.

[EJEMPLO 2 — riesgo BAJO]
PREGUNTA: ¿Cómo está mi balance?
RESPUESTA:
🔍 DIAGNÓSTICO
Tu balance actual de $1.200.000 COP supera tu promedio histórico de $900.000, señal positiva.
⚠️ NIVEL DE RIESGO: BAJO
Tienes liquidez saludable y una tasa de fallos del 2%.
💡 RECOMENDACIÓN
1. Considera mover el excedente a un ahorro de corto plazo.
2. Mantén al menos $400.000 como reserva de emergencia.
✅ ACCIÓN PARA HOY
Transfiere $200.000 a una cuenta de ahorro o CDT de bajo riesgo.\
"""

# Instrucción de idioma inyectada dinámicamente
_LANG_INSTRUCTIONS = {
    "es": "Responde completamente en español. No uses inglés bajo ninguna circunstancia.",
    "en": "Respond entirely in English. Do not use Spanish under any circumstances.",
}


# ══════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ══════════════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """
    Patrón Circuit Breaker para endpoints HTTP.

    CLOSED  → llamadas normales.
    OPEN    → bloquea llamadas por `cooldown_secs` tras `failure_threshold` fallos.
    HALF-OPEN → permite 1 intento de prueba al expirar el cooldown.
    """

    def __init__(self, name: str, failure_threshold: int, cooldown_secs: int) -> None:
        self.name = name
        self._threshold = failure_threshold
        self._cooldown = cooldown_secs
        self._failures = 0
        self._opened_at: Optional[float] = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at > self._cooldown:
            log.info(f"[CB:{self.name}] Cooldown expirado → HALF-OPEN, intentando de nuevo…")
            self._opened_at = None  # permite un intento de prueba
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = time.monotonic()
            log.warning(
                f"[CB:{self.name}] ABIERTO tras {self._failures} fallos. "
                f"Cooldown: {self._cooldown}s."
            )


_cb_llama  = CircuitBreaker("LLaMA",  CFG.cb_failure_threshold, CFG.cb_cooldown_secs)
_cb_claude = CircuitBreaker("Claude", CFG.cb_failure_threshold, CFG.cb_cooldown_secs)


# ══════════════════════════════════════════════════════════════════════════
# CACHE DE RESPUESTAS (LRU)
# ══════════════════════════════════════════════════════════════════════════

def _cache_key(user_context: str, question: str) -> str:
    """Hash SHA-256 truncado para usar como clave de cache."""
    raw = f"{user_context}||{question.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


_response_cache: Dict[str, str] = {}   # se limita con _evict_cache()
_cache_order: List[str] = []           # FIFO para LRU manual (sin dependencias extra)


def _cache_get(key: str) -> Optional[str]:
    return _response_cache.get(key)


def _cache_set(key: str, value: str) -> None:
    if key in _response_cache:
        return
    if len(_cache_order) >= CFG.cache_max_size:
        oldest = _cache_order.pop(0)
        _response_cache.pop(oldest, None)
    _response_cache[key] = value
    _cache_order.append(key)


# ══════════════════════════════════════════════════════════════════════════
# DETECCIÓN DE IDIOMA
# ══════════════════════════════════════════════════════════════════════════

_ES_WORDS = {
    "qué", "cómo", "cuál", "cuánto", "cuándo", "dónde", "quién",
    "estoy", "tengo", "gasto", "gasté", "saldo", "balance", "riesgo",
    "dinero", "deuda", "ahorro", "cuenta", "banco", "pago", "cobro",
    "hola", "dame", "dime", "ayuda", "resumen", "análisis", "situación",
    "financiero", "financiera", "transacción", "movimiento",
}

_EN_WORDS = {
    "what", "how", "which", "when", "where", "who", "my", "am", "is",
    "balance", "risk", "spend", "spent", "money", "debt", "saving",
    "account", "bank", "payment", "transaction", "summary", "analysis",
    "financial", "help", "show", "tell",
}


def detect_language(text: str) -> str:
    """Detecta idioma por intersección con wordlists. Default: 'es'."""
    words = set(text.lower().split())
    score_es = len(words & _ES_WORDS)
    score_en = len(words & _EN_WORDS)
    return "en" if score_en > score_es else "es"


# ══════════════════════════════════════════════════════════════════════════
# RIESGO FINANCIERO
# ══════════════════════════════════════════════════════════════════════════

def compute_risk_score(user_row: pd.Series) -> Tuple[int, str]:
    """
    Calcula un score de riesgo numérico (0–100) y su etiqueta.

=======
    Calcula un score de riesgo numérico (0–100) y su etiqueta.

>>>>>>> b8a43b0 (chore: remove data folder from repo)
    Ponderación:
      30 pts — estrés financiero combinado (is_financial_stress)
      25 pts — tasa de fallos alta (fail_ratio > 0.20)
      20 pts — balance bajo (is_low_balance)
      15 pts — usuario dormido (is_dormant)
      10 pts — fail_ratio moderado (0.10-0.20)
    """
    score = 0
    score += 30 * int(bool(user_row.get("financial_stress", 0)))
    score += 25 * int(bool(user_row.get("is_high_risk", 0)))
    score += 20 * int(bool(user_row.get("is_low_balance", 0)))
    score += 15 * int(bool(user_row.get("is_dormant", 0)))

    fail_ratio = float(user_row.get("fail_ratio", 0))
    if 0.10 <= fail_ratio < 0.20:
        score += 10

    score = min(score, 100)

    if score >= 50:
        label = "CRÍTICO"
    elif score >= 30:
        label = "ALTO"
    elif score >= 15:
        label = "MEDIO"
    else:
        label = "BAJO"

    return score, label


# ══════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DE CONTEXTO Y PROMPT
# ══════════════════════════════════════════════════════════════════════════

def build_user_context(user_row: pd.Series) -> str:
<<<<<<< HEAD
<<<<<<< HEAD
    """Construye el bloque de contexto financiero para el prompt."""
=======
    """Construye el contexto financiero del usuario para el LLM."""
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)
=======
    """Construye el bloque de contexto financiero para el prompt."""
>>>>>>> b8a43b0 (chore: remove data folder from repo)
    cat_cols = [c for c in user_row.index if c.startswith("cat_")]
    cat_info = {
        c.replace("cat_", "").capitalize(): f"${user_row.get(c, 0):,.0f} COP"
        for c in cat_cols
        if float(user_row.get(c, 0)) > 0
    }

<<<<<<< HEAD
<<<<<<< HEAD
    risk_score, risk_label = compute_risk_score(user_row)

    return (
        f"PERFIL DEL USUARIO:\n"
        f"  Nombre: {user_row.get('name', 'N/A')} | Edad: {user_row.get('age', 'N/A')} años\n"
        f"  Ciudad: {user_row.get('city', 'N/A')}, {user_row.get('country', 'N/A')}\n"
        f"  Segmento ML: {user_row.get('segment_icon', '')} {user_row.get('segment_name', 'N/A')}\n"
        f"\n"
        f"MÉTRICAS FINANCIERAS:\n"
        f"  Gasto total período:       ${user_row.get('total_spent', 0):,.0f} COP\n"
        f"  Transacción promedio:      ${user_row.get('avg_transaction', 0):,.0f} COP\n"
        f"  Transacción máxima:        ${user_row.get('max_transaction', 0):,.0f} COP\n"
        f"  Balance actual:            ${user_row.get('current_balance', 0):,.0f} COP\n"
        f"  Balance promedio histórico:${user_row.get('avg_balance', 0):,.0f} COP\n"
        f"\n"
        f"ACTIVIDAD:\n"
        f"  Transacciones totales:  {user_row.get('n_transactions', 0):.0f}\n"
        f"  Exitosas / Fallidas:    {user_row.get('n_success', 0):.0f} / {user_row.get('n_failed', 0):.0f}\n"
        f"  Tasa de fallos:         {float(user_row.get('fail_ratio', 0)) * 100:.1f}%\n"
        f"  Días activos:           {user_row.get('unique_days_active', 0):.0f}\n"
        f"  Hora pico:              {user_row.get('peak_hour', 'N/A')}:00 hrs\n"
        f"  Canal preferido:        {user_row.get('preferred_channel', 'N/A')}\n"
        f"\n"
        f"GASTO POR CATEGORÍA:\n"
        f"{json.dumps(cat_info, ensure_ascii=False, indent=2)}\n"
        f"\n"
        f"SEÑALES DE RIESGO (score calculado: {risk_score}/100 → {risk_label}):\n"
        f"  Premium / alto valor:      {'SÍ ✓' if user_row.get('is_high_value', 0) == 1 else 'NO'}\n"
        f"  Balance crítico (<$100k):  {'SÍ ⚠️' if user_row.get('is_low_balance', 0) == 1 else 'NO'}\n"
        f"  Alta tasa de fallos (>20%):{'SÍ ⚠️' if user_row.get('is_high_risk', 0) == 1 else 'NO'}\n"
        f"  Estrés financiero:         {'SÍ 🚨' if user_row.get('financial_stress', 0) == 1 else 'NO'}\n"
        f"  Usuario dormido (≤2 tx):   {'SÍ' if user_row.get('is_dormant', 0) == 1 else 'NO'}"
    )


def build_prompt(user_context: str, question: str, lang: str) -> str:
    """
    Ensambla el prompt completo para modelos sin chat-template nativo
    (Mistral raw, LLaMA raw).
    """
    lang_instruction = _LANG_INSTRUCTIONS.get(lang, _LANG_INSTRUCTIONS["es"])
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"══ INSTRUCCIÓN DE IDIOMA ══\n{lang_instruction}\n\n"
        f"══ CONTEXTO DEL USUARIO ══\n{user_context}\n\n"
        f"══ PREGUNTA ══\n{question}\n\n"
        f"══ RESPUESTA ══\n"
    )


def _build_chat_messages(
    user_context: str,
    question: str,
    history: List[Dict],
) -> List[Dict]:
    """
    Construye el historial de mensajes para endpoints OpenAI / Anthropic.
    Incluye los últimos `max_history_turns` turnos.
    """
    messages: List[Dict] = []

    # Historial recortado
    for turn in history[-(CFG.max_history_turns):]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    # Mensaje actual con contexto completo
    messages.append({
        "role": "user",
        "content": f"{user_context}\n\nPREGUNTA: {question}",
    })
    return messages


# ══════════════════════════════════════════════════════════════════════════
# VALIDADOR DE CALIDAD DE RESPUESTA
# ══════════════════════════════════════════════════════════════════════════

_HALLUCINATION_MARKERS = [
    "como modelo de lenguaje",
    "as an ai language model",
    "i cannot provide",
    "no tengo acceso",
    "no puedo acceder",
    "i don't have access to real",
    "```",                          # bloques de código nunca deben aparecer aquí
    "lorem ipsum",
]

_MIN_RESPONSE_LEN = 80   # respuestas más cortas se descartan


def _is_valid_response(text: str) -> bool:
    """
    Descarta respuestas que son demasiado cortas o contienen marcadores
    típicos de alucinación/negativa de un LLM.
    """
    if not text or len(text.strip()) < _MIN_RESPONSE_LEN:
        return False
    t_lower = text.lower()
    return not any(marker in t_lower for marker in _HALLUCINATION_MARKERS)


def _clean_response(text: str) -> str:
    """
    Post-procesa el output del LLM:
      • Elimina tokens especiales residuales
      • Recorta espacios y saltos de línea redundantes
      • Elimina el prefijo "RESPUESTA:" si el modelo lo repite
    """
    # Tokens especiales de Mistral / LLaMA
    for token in ["</s>", "<s>", "[INST]", "[/INST]", "<<SYS>>", "<</SYS>>"]:
        text = text.replace(token, "")

    # Quita prefijos que el modelo puede repetir del prompt
    for prefix in ["RESPUESTA:", "RESPONSE:", "ANSWER:"]:
        if text.strip().upper().startswith(prefix):
            text = text.strip()[len(prefix):].strip()

    # Normaliza saltos de línea múltiples
    import re
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ══════════════════════════════════════════════════════════════════════════
# RETRY CON EXPONENTIAL BACKOFF + JITTER
# ══════════════════════════════════════════════════════════════════════════

def _with_retry(fn, *args, retries: int = CFG.max_retries, base_delay: float = CFG.retry_base_delay, **kwargs):
    """
    Ejecuta `fn(*args, **kwargs)` con hasta `retries` reintentos.
    Delay: base_delay * 2^intento + jitter aleatorio (0-0.3s).
    Sólo reintenta en ConnectionError / Timeout, no en errores de autenticación.
    """
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as exc:
            last_exc = exc
            if attempt < retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.3)
                log.debug(f"Retry {attempt+1}/{retries} en {delay:.2f}s…")
                time.sleep(delay)
    raise last_exc


# ══════════════════════════════════════════════════════════════════════════
# BACKENDS DE INFERENCIA
# ══════════════════════════════════════════════════════════════════════════

def _try_llama(question: str, user_context: str, history: List[Dict]) -> Optional[str]:
    """
    Llama a LLaMA 3.2 vía endpoint OpenAI-compatible (vLLM / Ollama / LM Studio).
    Requiere: LLAMA_BASE_URL y opcionalmente LLAMA_MODEL en env.
    """
    if not CFG.llama_base_url:
        return None
    if _cb_llama.is_open:
        log.debug("[LLaMA] Circuit Breaker ABIERTO → skip.")
        return None

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += _build_chat_messages(user_context, question, history)

    def _call():
        return requests.post(
            f"{CFG.llama_base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model":             CFG.llama_model,
                "messages":          messages,
                "max_tokens":        CFG.max_tokens,
                "temperature":       CFG.temperature,
                "top_p":             0.92,
                "repetition_penalty": 1.1,
                "stream":            False,
            },
            timeout=CFG.request_timeout,
        )

    try:
        resp = _with_retry(_call)
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"]
            text = _clean_response(text)
            if _is_valid_response(text):
                _cb_llama.record_success()
                log.info(f"✅ LLaMA OK ({len(text)} chars)")
                return text
            log.warning("[LLaMA] Respuesta inválida/muy corta, descartada.")
            _cb_llama.record_failure()
        else:
            log.warning(f"[LLaMA] HTTP {resp.status_code}: {resp.text[:120]}")
            _cb_llama.record_failure()

    except Exception as exc:
        log.warning(f"[LLaMA] Error: {exc}")
        _cb_llama.record_failure()

    return None


def _try_mistral(question: str, user_context: str, lang: str) -> Optional[str]:
    """
    Inferencia local con Mistral 7B (sin red, sin API key).
    Usa `generate_response` del módulo mistral_local.py mejorado.
    """
    try:
        prompt = build_prompt(user_context, question, lang)
        text = generate_response(
            prompt,
            max_new_tokens=CFG.max_tokens,
            temperature=CFG.temperature,
        )
        text = _clean_response(text)
        if _is_valid_response(text):
            log.info(f"✅ Mistral OK ({len(text)} chars)")
            return text
        log.warning("[Mistral] Respuesta inválida/muy corta, descartada.")
    except Exception as exc:
        log.warning(f"[Mistral] Error: {exc}")
    return None


def _try_claude(
    question: str,
    user_context: str,
    history: List[Dict],
    api_key: str,
) -> Optional[str]:
    """
    Fallback a Claude API (Anthropic).
    Requiere: ANTHROPIC_API_KEY en env o parámetro explícito.
    """
    if not api_key:
        return None
    if _cb_claude.is_open:
        log.debug("[Claude] Circuit Breaker ABIERTO → skip.")
        return None

    messages = _build_chat_messages(user_context, question, history)

    def _call():
        return requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      CFG.claude_model,
                "max_tokens": CFG.max_tokens,
                "system":     SYSTEM_PROMPT,
                "messages":   messages,
            },
            timeout=CFG.request_timeout,
        )

    try:
        resp = _with_retry(_call)
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"]
            text = _clean_response(text)
            if _is_valid_response(text):
                _cb_claude.record_success()
                log.info(f"✅ Claude OK ({len(text)} chars)")
                return text
            log.warning("[Claude] Respuesta inválida/muy corta, descartada.")
            _cb_claude.record_failure()
        else:
            log.warning(f"[Claude] HTTP {resp.status_code}")
            _cb_claude.record_failure()

    except Exception as exc:
        log.warning(f"[Claude] Error: {exc}")
        _cb_claude.record_failure()
=======
    return f"""
PERFIL DEL USUARIO ({uid}):
  Nombre:   {user_row.get('name', 'N/A')} | Edad: {user_row.get('age', 'N/A')} años
  Ciudad:   {user_row.get('city', user_row.get('user_city', 'N/A'))}, {user_row.get('country', 'CO')}
  Segmento: {user_row.get('segment_icon', '')} {user_row.get('segment_name', 'N/A')} (cluster {user_row.get('cluster', '?')})
=======
    risk_score, risk_label = compute_risk_score(user_row)
>>>>>>> b8a43b0 (chore: remove data folder from repo)

    return (
        f"PERFIL DEL USUARIO:\n"
        f"  Nombre: {user_row.get('name', 'N/A')} | Edad: {user_row.get('age', 'N/A')} años\n"
        f"  Ciudad: {user_row.get('city', 'N/A')}, {user_row.get('country', 'N/A')}\n"
        f"  Segmento ML: {user_row.get('segment_icon', '')} {user_row.get('segment_name', 'N/A')}\n"
        f"\n"
        f"MÉTRICAS FINANCIERAS:\n"
        f"  Gasto total período:       ${user_row.get('total_spent', 0):,.0f} COP\n"
        f"  Transacción promedio:      ${user_row.get('avg_transaction', 0):,.0f} COP\n"
        f"  Transacción máxima:        ${user_row.get('max_transaction', 0):,.0f} COP\n"
        f"  Balance actual:            ${user_row.get('current_balance', 0):,.0f} COP\n"
        f"  Balance promedio histórico:${user_row.get('avg_balance', 0):,.0f} COP\n"
        f"\n"
        f"ACTIVIDAD:\n"
        f"  Transacciones totales:  {user_row.get('n_transactions', 0):.0f}\n"
        f"  Exitosas / Fallidas:    {user_row.get('n_success', 0):.0f} / {user_row.get('n_failed', 0):.0f}\n"
        f"  Tasa de fallos:         {float(user_row.get('fail_ratio', 0)) * 100:.1f}%\n"
        f"  Días activos:           {user_row.get('unique_days_active', 0):.0f}\n"
        f"  Hora pico:              {user_row.get('peak_hour', 'N/A')}:00 hrs\n"
        f"  Canal preferido:        {user_row.get('preferred_channel', 'N/A')}\n"
        f"\n"
        f"GASTO POR CATEGORÍA:\n"
        f"{json.dumps(cat_info, ensure_ascii=False, indent=2)}\n"
        f"\n"
        f"SEÑALES DE RIESGO (score calculado: {risk_score}/100 → {risk_label}):\n"
        f"  Premium / alto valor:      {'SÍ ✓' if user_row.get('is_high_value', 0) == 1 else 'NO'}\n"
        f"  Balance crítico (<$100k):  {'SÍ ⚠️' if user_row.get('is_low_balance', 0) == 1 else 'NO'}\n"
        f"  Alta tasa de fallos (>20%):{'SÍ ⚠️' if user_row.get('is_high_risk', 0) == 1 else 'NO'}\n"
        f"  Estrés financiero:         {'SÍ 🚨' if user_row.get('financial_stress', 0) == 1 else 'NO'}\n"
        f"  Usuario dormido (≤2 tx):   {'SÍ' if user_row.get('is_dormant', 0) == 1 else 'NO'}"
    )


def build_prompt(user_context: str, question: str, lang: str) -> str:
    """
    Ensambla el prompt completo para modelos sin chat-template nativo
    (Mistral raw, LLaMA raw).
    """
    lang_instruction = _LANG_INSTRUCTIONS.get(lang, _LANG_INSTRUCTIONS["es"])
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"══ INSTRUCCIÓN DE IDIOMA ══\n{lang_instruction}\n\n"
        f"══ CONTEXTO DEL USUARIO ══\n{user_context}\n\n"
        f"══ PREGUNTA ══\n{question}\n\n"
        f"══ RESPUESTA ══\n"
    )


def _build_chat_messages(
    user_context: str,
    question: str,
    history: List[Dict],
) -> List[Dict]:
    """
    Construye el historial de mensajes para endpoints OpenAI / Anthropic.
    Incluye los últimos `max_history_turns` turnos.
    """
    messages: List[Dict] = []

    # Historial recortado
    for turn in history[-(CFG.max_history_turns):]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    # Mensaje actual con contexto completo
    messages.append({
        "role": "user",
        "content": f"{user_context}\n\nPREGUNTA: {question}",
    })
    return messages


# ══════════════════════════════════════════════════════════════════════════
# VALIDADOR DE CALIDAD DE RESPUESTA
# ══════════════════════════════════════════════════════════════════════════

_HALLUCINATION_MARKERS = [
    "como modelo de lenguaje",
    "as an ai language model",
    "i cannot provide",
    "no tengo acceso",
    "no puedo acceder",
    "i don't have access to real",
    "```",                          # bloques de código nunca deben aparecer aquí
    "lorem ipsum",
]

<<<<<<< HEAD
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
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)
=======
_MIN_RESPONSE_LEN = 80   # respuestas más cortas se descartan
>>>>>>> b8a43b0 (chore: remove data folder from repo)


def _is_valid_response(text: str) -> bool:
    """
    Descarta respuestas que son demasiado cortas o contienen marcadores
    típicos de alucinación/negativa de un LLM.
    """
    if not text or len(text.strip()) < _MIN_RESPONSE_LEN:
        return False
    t_lower = text.lower()
    return not any(marker in t_lower for marker in _HALLUCINATION_MARKERS)


def _clean_response(text: str) -> str:
    """
    Post-procesa el output del LLM:
      • Elimina tokens especiales residuales
      • Recorta espacios y saltos de línea redundantes
      • Elimina el prefijo "RESPUESTA:" si el modelo lo repite
    """
    # Tokens especiales de Mistral / LLaMA
    for token in ["</s>", "<s>", "[INST]", "[/INST]", "<<SYS>>", "<</SYS>>"]:
        text = text.replace(token, "")

    # Quita prefijos que el modelo puede repetir del prompt
    for prefix in ["RESPUESTA:", "RESPONSE:", "ANSWER:"]:
        if text.strip().upper().startswith(prefix):
            text = text.strip()[len(prefix):].strip()

    # Normaliza saltos de línea múltiples
    import re
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ══════════════════════════════════════════════════════════════════════════
# RETRY CON EXPONENTIAL BACKOFF + JITTER
# ══════════════════════════════════════════════════════════════════════════

def _with_retry(fn, *args, retries: int = CFG.max_retries, base_delay: float = CFG.retry_base_delay, **kwargs):
    """
    Ejecuta `fn(*args, **kwargs)` con hasta `retries` reintentos.
    Delay: base_delay * 2^intento + jitter aleatorio (0-0.3s).
    Sólo reintenta en ConnectionError / Timeout, no en errores de autenticación.
    """
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as exc:
            last_exc = exc
            if attempt < retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.3)
                log.debug(f"Retry {attempt+1}/{retries} en {delay:.2f}s…")
                time.sleep(delay)
    raise last_exc


# ══════════════════════════════════════════════════════════════════════════
# BACKENDS DE INFERENCIA
# ══════════════════════════════════════════════════════════════════════════

def _try_llama(question: str, user_context: str, history: List[Dict]) -> Optional[str]:
    """
    Llama a LLaMA 3.2 vía endpoint OpenAI-compatible (vLLM / Ollama / LM Studio).
    Requiere: LLAMA_BASE_URL y opcionalmente LLAMA_MODEL en env.
    """
    if not CFG.llama_base_url:
        return None
    if _cb_llama.is_open:
        log.debug("[LLaMA] Circuit Breaker ABIERTO → skip.")
        return None

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += _build_chat_messages(user_context, question, history)

    def _call():
        return requests.post(
            f"{CFG.llama_base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model":             CFG.llama_model,
                "messages":          messages,
                "max_tokens":        CFG.max_tokens,
                "temperature":       CFG.temperature,
                "top_p":             0.92,
                "repetition_penalty": 1.1,
                "stream":            False,
            },
            timeout=CFG.request_timeout,
        )

    try:
        resp = _with_retry(_call)
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"]
            text = _clean_response(text)
            if _is_valid_response(text):
                _cb_llama.record_success()
                log.info(f"✅ LLaMA OK ({len(text)} chars)")
                return text
            log.warning("[LLaMA] Respuesta inválida/muy corta, descartada.")
            _cb_llama.record_failure()
        else:
            log.warning(f"[LLaMA] HTTP {resp.status_code}: {resp.text[:120]}")
            _cb_llama.record_failure()

    except Exception as exc:
        log.warning(f"[LLaMA] Error: {exc}")
        _cb_llama.record_failure()

    return None


def _try_mistral(question: str, user_context: str, lang: str) -> Optional[str]:
    """
    Inferencia local con Mistral 7B (sin red, sin API key).
    Usa `generate_response` del módulo mistral_local.py mejorado.
    """
    try:
        prompt = build_prompt(user_context, question, lang)
        text = generate_response(
            prompt,
            max_new_tokens=CFG.max_tokens,
            temperature=CFG.temperature,
        )
        text = _clean_response(text)
        if _is_valid_response(text):
            log.info(f"✅ Mistral OK ({len(text)} chars)")
            return text
        log.warning("[Mistral] Respuesta inválida/muy corta, descartada.")
    except Exception as exc:
        log.warning(f"[Mistral] Error: {exc}")
    return None


def _try_claude(
    question: str,
    user_context: str,
    history: List[Dict],
    api_key: str,
) -> Optional[str]:
    """
    Fallback a Claude API (Anthropic).
    Requiere: ANTHROPIC_API_KEY en env o parámetro explícito.
    """
    if not api_key:
        return None
    if _cb_claude.is_open:
        log.debug("[Claude] Circuit Breaker ABIERTO → skip.")
        return None

    messages = _build_chat_messages(user_context, question, history)

    def _call():
        return requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      CFG.claude_model,
                "max_tokens": CFG.max_tokens,
                "system":     SYSTEM_PROMPT,
                "messages":   messages,
            },
            timeout=CFG.request_timeout,
        )

    try:
        resp = _with_retry(_call)
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"]
            text = _clean_response(text)
            if _is_valid_response(text):
                _cb_claude.record_success()
                log.info(f"✅ Claude OK ({len(text)} chars)")
                return text
            log.warning("[Claude] Respuesta inválida/muy corta, descartada.")
            _cb_claude.record_failure()
        else:
            log.warning(f"[Claude] HTTP {resp.status_code}")
            _cb_claude.record_failure()

    except Exception as exc:
        log.warning(f"[Claude] Error: {exc}")
        _cb_claude.record_failure()

    return None


# ══════════════════════════════════════════════════════════════════════════
<<<<<<< HEAD
<<<<<<< HEAD
# FALLBACK POR REGLAS — completo y accionable
=======
# FALLBACK POR REGLAS — siempre disponible, < 1ms
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)
=======
# FALLBACK POR REGLAS — completo y accionable
>>>>>>> b8a43b0 (chore: remove data folder from repo)
# ══════════════════════════════════════════════════════════════════════════

def _rule_based_fallback(question: str, user_row: pd.Series, lang: str) -> str:
    """
    Respuestas determinísticas de alta calidad.
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> b8a43b0 (chore: remove data folder from repo)
    Latencia: ~0ms. Sin dependencias externas. NUNCA lanza excepciones.

    Cubre 4 categorías de pregunta:
      • Riesgo financiero
      • Composición del gasto
      • Estado del balance
      • Resumen / consulta genérica
<<<<<<< HEAD
    """
    q = question.lower()
    risk_score, risk_label = compute_risk_score(user_row)

    # Datos clave
    balance     = float(user_row.get("current_balance", 0))
    avg_balance = float(user_row.get("avg_balance", 1) or 1)
    fail_ratio  = float(user_row.get("fail_ratio", 0))
    total_spent = float(user_row.get("total_spent", 0))
    segment     = user_row.get("segment_name", "N/A")
    name        = user_row.get("name", "")

    # Categoría dominante de gasto
    cat_cols = [c for c in user_row.index if c.startswith("cat_")]
    cat_amounts = {c.replace("cat_", "").capitalize(): float(user_row.get(c, 0)) for c in cat_cols}
    top_cat = max(cat_amounts, key=cat_amounts.get) if cat_amounts else None
    top_cat_pct = (cat_amounts[top_cat] / total_spent * 100) if top_cat and total_spent > 0 else 0

    # ── ¿Pregunta sobre riesgo? ───────────────────────────────────────────
    risk_keywords = {
        "es": ["riesgo", "peligro", "alerta", "problema", "crisis", "estoy mal"],
        "en": ["risk", "danger", "alert", "problem", "crisis", "in trouble"],
    }
    if any(kw in q for kw in risk_keywords.get(lang, risk_keywords["es"]) + risk_keywords["en"]):
        if lang == "en":
            return (
                f"🔍 DIAGNÓSTICO\n"
                f"Your risk score is {risk_score}/100 ({risk_label})."
                f"{' High failure rate (' + f'{fail_ratio*100:.0f}%' + ') signals payment issues.' if fail_ratio > 0.15 else ''}"
                f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
                f"{'Multiple risk signals detected simultaneously.' if risk_score >= 50 else 'Situation is manageable with corrective actions.'}"
                f"\n\n💡 RECOMENDACIÓN\n"
                f"1. {'Immediately stop non-essential spending.' if risk_score >= 50 else 'Monitor your balance daily.'}\n"
                f"2. {'Contact your bank to review payment failures.' if fail_ratio > 0.15 else 'Keep at least $200,000 COP as emergency reserve.'}\n"
                f"3. Set a daily spending limit on your app."
                f"\n\n✅ ACCIÓN PARA HOY\n"
                f"{'Call your bank and review the last 5 failed transactions.' if fail_ratio > 0.15 else 'Set a spending alert at 80% of your current balance.'}"
            )
        return (
            f"🔍 DIAGNÓSTICO\n"
            f"Tu score de riesgo es {risk_score}/100 ({risk_label})."
            f"{' Tasa de fallos del ' + f'{fail_ratio*100:.0f}%' + ' indica problemas de pago.' if fail_ratio > 0.15 else ''}"
            f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
            f"{'Múltiples señales de alerta activas simultáneamente.' if risk_score >= 50 else 'La situación es manejable con acciones correctivas.'}"
            f"\n\n💡 RECOMENDACIÓN\n"
            f"1. {'Congela gastos no esenciales de inmediato.' if risk_score >= 50 else 'Monitorea tu saldo diariamente.'}\n"
            f"2. {'Contacta a tu banco sobre los pagos fallidos.' if fail_ratio > 0.15 else 'Mantén mínimo $200.000 COP de reserva de emergencia.'}\n"
            f"3. Activa alertas de saldo en la app."
            f"\n\n✅ ACCIÓN PARA HOY\n"
            f"{'Llama a tu banco y revisa las últimas 5 transacciones fallidas.' if fail_ratio > 0.15 else 'Configura una alerta de saldo al 80% del balance actual.'}"
        )

    # ── ¿Pregunta sobre gasto / categorías? ──────────────────────────────
    spend_keywords = {
        "es": ["gasto", "gast", "categor", "compr", "dinero", "más dinero"],
        "en": ["spend", "spent", "categor", "purchase", "money", "most"],
    }
    if any(kw in q for kw in spend_keywords.get(lang, spend_keywords["es"]) + spend_keywords["en"]):
        cat_lines = "\n".join(
            f"  • {cat}: ${amt:,.0f} COP ({amt/total_spent*100:.0f}%)"
            for cat, amt in sorted(cat_amounts.items(), key=lambda x: -x[1])
            if amt > 0
        ) or "  (sin datos de categorías)"

        if lang == "en":
            return (
                f"🔍 DIAGNÓSTICO\n"
                f"Your main spending category is {top_cat} ({top_cat_pct:.0f}% of total)."
                f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
                f"{'Concentration in one category above 60% is a risk signal.' if top_cat_pct > 60 else 'Your spending is reasonably distributed.'}"
                f"\n\n💡 RECOMENDACIÓN\n"
                f"Spending breakdown:\n{cat_lines}\n"
                f"1. {'Review ' + top_cat + ' expenses — they dominate your budget.' if top_cat_pct > 50 else 'Continue with this distribution, it is balanced.'}\n"
                f"2. Set category limits for the next month."
                f"\n\n✅ ACCIÓN PARA HOY\n"
                f"Open your transaction history and identify the 3 largest {top_cat} expenses this period."
            )
        return (
            f"🔍 DIAGNÓSTICO\n"
            f"Tu categoría de mayor gasto es {top_cat} ({top_cat_pct:.0f}% del total)."
            f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
            f"{'Concentración superior al 60% en una categoría es señal de alerta.' if top_cat_pct > 60 else 'Tu distribución de gasto es razonablemente balanceada.'}"
            f"\n\n💡 RECOMENDACIÓN\n"
            f"Desglose de gastos:\n{cat_lines}\n"
            f"1. {'Revisa los gastos en ' + str(top_cat) + ' — dominan tu presupuesto.' if top_cat_pct > 50 else 'Continúa con esta distribución, está equilibrada.'}\n"
            f"2. Establece límites por categoría para el próximo mes."
            f"\n\n✅ ACCIÓN PARA HOY\n"
            f"Abre tu historial y encuentra los 3 gastos más grandes en {top_cat} de este período."
        )

    # ── ¿Pregunta sobre balance / saldo? ─────────────────────────────────
    balance_keywords = {
        "es": ["balance", "saldo", "cuenta", "dinero tengo", "tengo disponible"],
        "en": ["balance", "account", "available", "how much"],
    }
    if any(kw in q for kw in balance_keywords.get(lang, balance_keywords["es"]) + balance_keywords["en"]):
        trend = "por encima" if balance > avg_balance else "por debajo"
        pct_diff = abs(balance - avg_balance) / avg_balance * 100 if avg_balance else 0

        if lang == "en":
            return (
                f"🔍 DIAGNÓSTICO\n"
                f"Your current balance is ${balance:,.0f} COP, "
                f"{trend.replace('por encima', 'above').replace('por debajo', 'below')} your historical average by {pct_diff:.0f}%."
                f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
                f"{'Balance below historical average is a warning sign.' if balance < avg_balance else 'Balance above average is a positive indicator.'}"
                f"\n\n💡 RECOMENDACIÓN\n"
                f"1. {'Urgently reduce discretionary spending.' if balance < 100_000 else 'Maintain at least $200,000 COP as emergency fund.'}\n"
                f"2. {'Consider moving surplus to a savings account.' if balance > avg_balance * 1.3 else 'Review recurring expenses to optimize your balance.'}"
                f"\n\n✅ ACCIÓN PARA HOY\n"
                f"{'Transfer at least $100,000 COP to a savings account.' if balance > avg_balance else 'Identify one recurring expense you can pause today.'}"
            )
        return (
            f"🔍 DIAGNÓSTICO\n"
            f"Tu balance actual es ${balance:,.0f} COP, "
            f"{trend} de tu promedio histórico un {pct_diff:.0f}%."
            f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
            f"{'Balance por debajo del histórico es señal de alerta.' if balance < avg_balance else 'Balance superior al promedio es indicador positivo.'}"
            f"\n\n💡 RECOMENDACIÓN\n"
            f"1. {'Reduce gastos discrecionales de manera urgente.' if balance < 100_000 else 'Mantén al menos $200.000 COP como fondo de emergencia.'}\n"
            f"2. {'Considera mover el excedente a ahorro.' if balance > avg_balance * 1.3 else 'Revisa gastos recurrentes para optimizar tu saldo.'}"
            f"\n\n✅ ACCIÓN PARA HOY\n"
            f"{'Transfiere al menos $100.000 COP a una cuenta de ahorro.' if balance > avg_balance else 'Identifica un gasto recurrente que puedas pausar hoy.'}"
        )

    # ── Resumen general / consulta no reconocida ──────────────────────────
    if lang == "en":
        return (
            f"🔍 DIAGNÓSTICO\n"
            f"Summary for {name} (Segment: {segment}): "
            f"balance ${balance:,.0f} COP, spent ${total_spent:,.0f} COP, "
            f"risk {risk_score}/100 ({risk_label})."
            f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
            f"{'Immediate action recommended.' if risk_score >= 50 else 'Situation is under control with minor adjustments needed.'}"
            f"\n\n💡 RECOMENDACIÓN\n"
            f"1. {'Address risk signals urgently.' if risk_score >= 50 else 'Continue your current financial habits.'}\n"
            f"2. {'Review failed transactions immediately.' if fail_ratio > 0.15 else 'Consider saving 10% of your monthly income.'}\n"
            f"3. Set monthly budget goals per category."
            f"\n\n✅ ACCIÓN PARA HOY\n"
            f"Review your last 10 transactions and classify each as essential or optional."
        )
    return (
        f"🔍 DIAGNÓSTICO\n"
        f"Resumen de {name} (Segmento: {segment}): "
        f"balance ${balance:,.0f} COP, gasto ${total_spent:,.0f} COP, "
        f"riesgo {risk_score}/100 ({risk_label})."
        f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
        f"{'Se recomienda acción inmediata.' if risk_score >= 50 else 'Situación bajo control con ajustes menores necesarios.'}"
        f"\n\n💡 RECOMENDACIÓN\n"
        f"1. {'Atiende las señales de riesgo de manera urgente.' if risk_score >= 50 else 'Continúa tus hábitos financieros actuales.'}\n"
        f"2. {'Revisa transacciones fallidas de inmediato.' if fail_ratio > 0.15 else 'Considera ahorrar el 10% de tu ingreso mensual.'}\n"
        f"3. Establece metas de presupuesto mensual por categoría."
        f"\n\n✅ ACCIÓN PARA HOY\n"
        f"Revisa tus últimas 10 transacciones y clasifica cada una como esencial u opcional."
=======
    Sin dependencias externas. Latencia < 1ms.
=======
>>>>>>> b8a43b0 (chore: remove data folder from repo)
    """
    q = question.lower()
    risk_score, risk_label = compute_risk_score(user_row)

    # Datos clave
    balance     = float(user_row.get("current_balance", 0))
    avg_balance = float(user_row.get("avg_balance", 1) or 1)
    fail_ratio  = float(user_row.get("fail_ratio", 0))
    total_spent = float(user_row.get("total_spent", 0))
    segment     = user_row.get("segment_name", "N/A")
    name        = user_row.get("name", "")

    # Categoría dominante de gasto
    cat_cols = [c for c in user_row.index if c.startswith("cat_")]
    cat_amounts = {c.replace("cat_", "").capitalize(): float(user_row.get(c, 0)) for c in cat_cols}
    top_cat = max(cat_amounts, key=cat_amounts.get) if cat_amounts else None
    top_cat_pct = (cat_amounts[top_cat] / total_spent * 100) if top_cat and total_spent > 0 else 0

    # ── ¿Pregunta sobre riesgo? ───────────────────────────────────────────
    risk_keywords = {
        "es": ["riesgo", "peligro", "alerta", "problema", "crisis", "estoy mal"],
        "en": ["risk", "danger", "alert", "problem", "crisis", "in trouble"],
    }
    if any(kw in q for kw in risk_keywords.get(lang, risk_keywords["es"]) + risk_keywords["en"]):
        if lang == "en":
            return (
                f"🔍 DIAGNÓSTICO\n"
                f"Your risk score is {risk_score}/100 ({risk_label})."
                f"{' High failure rate (' + f'{fail_ratio*100:.0f}%' + ') signals payment issues.' if fail_ratio > 0.15 else ''}"
                f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
                f"{'Multiple risk signals detected simultaneously.' if risk_score >= 50 else 'Situation is manageable with corrective actions.'}"
                f"\n\n💡 RECOMENDACIÓN\n"
                f"1. {'Immediately stop non-essential spending.' if risk_score >= 50 else 'Monitor your balance daily.'}\n"
                f"2. {'Contact your bank to review payment failures.' if fail_ratio > 0.15 else 'Keep at least $200,000 COP as emergency reserve.'}\n"
                f"3. Set a daily spending limit on your app."
                f"\n\n✅ ACCIÓN PARA HOY\n"
                f"{'Call your bank and review the last 5 failed transactions.' if fail_ratio > 0.15 else 'Set a spending alert at 80% of your current balance.'}"
            )
        return (
            f"🔍 DIAGNÓSTICO\n"
            f"Tu score de riesgo es {risk_score}/100 ({risk_label})."
            f"{' Tasa de fallos del ' + f'{fail_ratio*100:.0f}%' + ' indica problemas de pago.' if fail_ratio > 0.15 else ''}"
            f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
            f"{'Múltiples señales de alerta activas simultáneamente.' if risk_score >= 50 else 'La situación es manejable con acciones correctivas.'}"
            f"\n\n💡 RECOMENDACIÓN\n"
            f"1. {'Congela gastos no esenciales de inmediato.' if risk_score >= 50 else 'Monitorea tu saldo diariamente.'}\n"
            f"2. {'Contacta a tu banco sobre los pagos fallidos.' if fail_ratio > 0.15 else 'Mantén mínimo $200.000 COP de reserva de emergencia.'}\n"
            f"3. Activa alertas de saldo en la app."
            f"\n\n✅ ACCIÓN PARA HOY\n"
            f"{'Llama a tu banco y revisa las últimas 5 transacciones fallidas.' if fail_ratio > 0.15 else 'Configura una alerta de saldo al 80% del balance actual.'}"
        )

    # ── ¿Pregunta sobre gasto / categorías? ──────────────────────────────
    spend_keywords = {
        "es": ["gasto", "gast", "categor", "compr", "dinero", "más dinero"],
        "en": ["spend", "spent", "categor", "purchase", "money", "most"],
    }
    if any(kw in q for kw in spend_keywords.get(lang, spend_keywords["es"]) + spend_keywords["en"]):
        cat_lines = "\n".join(
            f"  • {cat}: ${amt:,.0f} COP ({amt/total_spent*100:.0f}%)"
            for cat, amt in sorted(cat_amounts.items(), key=lambda x: -x[1])
            if amt > 0
        ) or "  (sin datos de categorías)"

        if lang == "en":
            return (
                f"🔍 DIAGNÓSTICO\n"
                f"Your main spending category is {top_cat} ({top_cat_pct:.0f}% of total)."
                f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
                f"{'Concentration in one category above 60% is a risk signal.' if top_cat_pct > 60 else 'Your spending is reasonably distributed.'}"
                f"\n\n💡 RECOMENDACIÓN\n"
                f"Spending breakdown:\n{cat_lines}\n"
                f"1. {'Review ' + top_cat + ' expenses — they dominate your budget.' if top_cat_pct > 50 else 'Continue with this distribution, it is balanced.'}\n"
                f"2. Set category limits for the next month."
                f"\n\n✅ ACCIÓN PARA HOY\n"
                f"Open your transaction history and identify the 3 largest {top_cat} expenses this period."
            )
        return (
            f"🔍 DIAGNÓSTICO\n"
            f"Tu categoría de mayor gasto es {top_cat} ({top_cat_pct:.0f}% del total)."
            f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
            f"{'Concentración superior al 60% en una categoría es señal de alerta.' if top_cat_pct > 60 else 'Tu distribución de gasto es razonablemente balanceada.'}"
            f"\n\n💡 RECOMENDACIÓN\n"
            f"Desglose de gastos:\n{cat_lines}\n"
            f"1. {'Revisa los gastos en ' + str(top_cat) + ' — dominan tu presupuesto.' if top_cat_pct > 50 else 'Continúa con esta distribución, está equilibrada.'}\n"
            f"2. Establece límites por categoría para el próximo mes."
            f"\n\n✅ ACCIÓN PARA HOY\n"
            f"Abre tu historial y encuentra los 3 gastos más grandes en {top_cat} de este período."
        )

    # ── ¿Pregunta sobre balance / saldo? ─────────────────────────────────
    balance_keywords = {
        "es": ["balance", "saldo", "cuenta", "dinero tengo", "tengo disponible"],
        "en": ["balance", "account", "available", "how much"],
    }
    if any(kw in q for kw in balance_keywords.get(lang, balance_keywords["es"]) + balance_keywords["en"]):
        trend = "por encima" if balance > avg_balance else "por debajo"
        pct_diff = abs(balance - avg_balance) / avg_balance * 100 if avg_balance else 0

        if lang == "en":
            return (
                f"🔍 DIAGNÓSTICO\n"
                f"Your current balance is ${balance:,.0f} COP, "
                f"{trend.replace('por encima', 'above').replace('por debajo', 'below')} your historical average by {pct_diff:.0f}%."
                f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
                f"{'Balance below historical average is a warning sign.' if balance < avg_balance else 'Balance above average is a positive indicator.'}"
                f"\n\n💡 RECOMENDACIÓN\n"
                f"1. {'Urgently reduce discretionary spending.' if balance < 100_000 else 'Maintain at least $200,000 COP as emergency fund.'}\n"
                f"2. {'Consider moving surplus to a savings account.' if balance > avg_balance * 1.3 else 'Review recurring expenses to optimize your balance.'}"
                f"\n\n✅ ACCIÓN PARA HOY\n"
                f"{'Transfer at least $100,000 COP to a savings account.' if balance > avg_balance else 'Identify one recurring expense you can pause today.'}"
            )
        return (
            f"🔍 DIAGNÓSTICO\n"
            f"Tu balance actual es ${balance:,.0f} COP, "
            f"{trend} de tu promedio histórico un {pct_diff:.0f}%."
            f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
            f"{'Balance por debajo del histórico es señal de alerta.' if balance < avg_balance else 'Balance superior al promedio es indicador positivo.'}"
            f"\n\n💡 RECOMENDACIÓN\n"
            f"1. {'Reduce gastos discrecionales de manera urgente.' if balance < 100_000 else 'Mantén al menos $200.000 COP como fondo de emergencia.'}\n"
            f"2. {'Considera mover el excedente a ahorro.' if balance > avg_balance * 1.3 else 'Revisa gastos recurrentes para optimizar tu saldo.'}"
            f"\n\n✅ ACCIÓN PARA HOY\n"
            f"{'Transfiere al menos $100.000 COP a una cuenta de ahorro.' if balance > avg_balance else 'Identifica un gasto recurrente que puedas pausar hoy.'}"
        )

    # ── Resumen general / consulta no reconocida ──────────────────────────
    if lang == "en":
        return (
            f"🔍 DIAGNÓSTICO\n"
            f"Summary for {name} (Segment: {segment}): "
            f"balance ${balance:,.0f} COP, spent ${total_spent:,.0f} COP, "
            f"risk {risk_score}/100 ({risk_label})."
            f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
            f"{'Immediate action recommended.' if risk_score >= 50 else 'Situation is under control with minor adjustments needed.'}"
            f"\n\n💡 RECOMENDACIÓN\n"
            f"1. {'Address risk signals urgently.' if risk_score >= 50 else 'Continue your current financial habits.'}\n"
            f"2. {'Review failed transactions immediately.' if fail_ratio > 0.15 else 'Consider saving 10% of your monthly income.'}\n"
            f"3. Set monthly budget goals per category."
            f"\n\n✅ ACCIÓN PARA HOY\n"
            f"Review your last 10 transactions and classify each as essential or optional."
        )
    return (
<<<<<<< HEAD
        f"Hola {name} ({seg_ico} {seg}), gasto ${spent:,.0f} COP | balance ${balance:,.0f} COP.\n\n"
        f"Pregúntame sobre: gastos, riesgo, balance, patrones o pide un resumen completo.\n\n"
        f"💡 *Modo offline activo — configura `MISTRAL_BASE_URL` para análisis con IA generativa.*"
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)
=======
        f"🔍 DIAGNÓSTICO\n"
        f"Resumen de {name} (Segmento: {segment}): "
        f"balance ${balance:,.0f} COP, gasto ${total_spent:,.0f} COP, "
        f"riesgo {risk_score}/100 ({risk_label})."
        f"\n\n⚠️ NIVEL DE RIESGO: {risk_label}\n"
        f"{'Se recomienda acción inmediata.' if risk_score >= 50 else 'Situación bajo control con ajustes menores necesarios.'}"
        f"\n\n💡 RECOMENDACIÓN\n"
        f"1. {'Atiende las señales de riesgo de manera urgente.' if risk_score >= 50 else 'Continúa tus hábitos financieros actuales.'}\n"
        f"2. {'Revisa transacciones fallidas de inmediato.' if fail_ratio > 0.15 else 'Considera ahorrar el 10% de tu ingreso mensual.'}\n"
        f"3. Establece metas de presupuesto mensual por categoría."
        f"\n\n✅ ACCIÓN PARA HOY\n"
        f"Revisa tus últimas 10 transacciones y clasifica cada una como esencial u opcional."
>>>>>>> b8a43b0 (chore: remove data folder from repo)
    )


# ══════════════════════════════════════════════════════════════════════════
# FUNCIÓN PÚBLICA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

def ask_agent(
    question: str,
<<<<<<< HEAD
<<<<<<< HEAD
    user_row: pd.Series,
    history: Optional[List[Dict]] = None,
    api_key: Optional[str] = None,
=======
    user_row:  pd.Series,
    history:   List[Dict] = None,
    api_key:   str = None,          # mantenido por compatibilidad, ya no se usa en main flow
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)
=======
    user_row: pd.Series,
    history: Optional[List[Dict]] = None,
    api_key: Optional[str] = None,
>>>>>>> b8a43b0 (chore: remove data folder from repo)
) -> Tuple[str, List[Dict], str]:
    """
    Punto de entrada principal del agente.

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> b8a43b0 (chore: remove data folder from repo)
    Args:
        question:  Pregunta del usuario (español o inglés).
        user_row:  Fila de pandas con el perfil financiero.
        history:   Turnos anteriores [{'role': 'user'|'assistant', 'content': str}].
        api_key:   API key de Anthropic (opcional, se lee de env si no se pasa).
<<<<<<< HEAD

    Returns:
        (answer, new_history, mode)
          answer:      Texto de respuesta.
          new_history: Historial actualizado con este turno.
          mode:        Backend usado: 'llama' | 'mistral' | 'claude' | 'rules' | 'cache'.
    """
    request_id = uuid.uuid4().hex[:8]
    history = history or []
    t0 = time.perf_counter()

    log.info(f"[{request_id}] Pregunta: {question!r}")

    # ── Detección de idioma ───────────────────────────────────────────────
    lang = detect_language(question)

    # ── Construcción de contexto ──────────────────────────────────────────
    user_context = build_user_context(user_row)

    # ── Cache lookup ──────────────────────────────────────────────────────
    cache_k = _cache_key(user_context, question)
    cached = _cache_get(cache_k)
    if cached:
        log.info(f"[{request_id}] ✅ Cache HIT")
        new_history = history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": cached},
        ]
        return cached, new_history, "cache"

    answer: Optional[str] = None
    mode = "rules"

    # ── 1️⃣  LLaMA (máxima prioridad si está disponible) ─────────────────
    answer = _try_llama(question, user_context, history)
=======
    Prioridad: Mistral-7B → LLaMA → Offline
=======
>>>>>>> b8a43b0 (chore: remove data folder from repo)

    Returns:
        (answer, new_history, mode)
          answer:      Texto de respuesta.
          new_history: Historial actualizado con este turno.
          mode:        Backend usado: 'llama' | 'mistral' | 'claude' | 'rules' | 'cache'.
    """
    request_id = uuid.uuid4().hex[:8]
    history = history or []
    t0 = time.perf_counter()

    log.info(f"[{request_id}] Pregunta: {question!r}")

    # ── Detección de idioma ───────────────────────────────────────────────
    lang = detect_language(question)

    # ── Construcción de contexto ──────────────────────────────────────────
    user_context = build_user_context(user_row)

<<<<<<< HEAD
    # 1️⃣  Mistral-7B (fine-tuned Tesla T4)
    answer = _try_mistral(question, user_context, history)
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)
=======
    # ── Cache lookup ──────────────────────────────────────────────────────
    cache_k = _cache_key(user_context, question)
    cached = _cache_get(cache_k)
    if cached:
        log.info(f"[{request_id}] ✅ Cache HIT")
        new_history = history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": cached},
        ]
        return cached, new_history, "cache"

    answer: Optional[str] = None
    mode = "rules"

    # ── 1️⃣  LLaMA (máxima prioridad si está disponible) ─────────────────
    answer = _try_llama(question, user_context, history)
>>>>>>> b8a43b0 (chore: remove data folder from repo)
    if answer:
        mode = "llama"

<<<<<<< HEAD
<<<<<<< HEAD
    # ── 2️⃣  Mistral local ────────────────────────────────────────────────
    if not answer:
        answer = _try_mistral(question, user_context, lang)
        if answer:
            mode = "mistral"

    # ── 3️⃣  Claude API ───────────────────────────────────────────────────
    if not answer:
        key = api_key or CFG.anthropic_api_key
        answer = _try_claude(question, user_context, history, key)
=======
    # 2️⃣  LLaMA (fallback GPU secundario)
    if not answer:
        answer = _try_llama(question, user_context, history)
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)
=======
    # ── 2️⃣  Mistral local ────────────────────────────────────────────────
    if not answer:
        answer = _try_mistral(question, user_context, lang)
>>>>>>> b8a43b0 (chore: remove data folder from repo)
        if answer:
            mode = "mistral"

<<<<<<< HEAD
<<<<<<< HEAD
    # ── 4️⃣  Fallback por reglas (NUNCA falla) ────────────────────────────
    if not answer:
        answer = _rule_based_fallback(question, user_row, lang)
        mode = "rules"

    # ── Cache write ───────────────────────────────────────────────────────
    if mode != "rules":   # las reglas son determinísticas → no vale la pena cachear
        _cache_set(cache_k, answer)

    # ── Historial ─────────────────────────────────────────────────────────
=======
    # 3️⃣  Reglas determinísticas (siempre funciona)
=======
    # ── 3️⃣  Claude API ───────────────────────────────────────────────────
>>>>>>> b8a43b0 (chore: remove data folder from repo)
    if not answer:
        key = api_key or CFG.anthropic_api_key
        answer = _try_claude(question, user_context, history, key)
        if answer:
            mode = "claude"

<<<<<<< HEAD
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)
=======
    # ── 4️⃣  Fallback por reglas (NUNCA falla) ────────────────────────────
    if not answer:
        answer = _rule_based_fallback(question, user_row, lang)
        mode = "rules"

    # ── Cache write ───────────────────────────────────────────────────────
    if mode != "rules":   # las reglas son determinísticas → no vale la pena cachear
        _cache_set(cache_k, answer)

    # ── Historial ─────────────────────────────────────────────────────────
>>>>>>> b8a43b0 (chore: remove data folder from repo)
    new_history = history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> b8a43b0 (chore: remove data folder from repo)

    elapsed = (time.perf_counter() - t0) * 1000
    log.info(f"[{request_id}] modo='{mode}' | {len(answer)} chars | {elapsed:.0f}ms")

    return answer, new_history, mode
<<<<<<< HEAD
=======
    logger.info(f"Agent mode: {mode} | chars: {len(answer)}")
    return answer, new_history, mode
>>>>>>> fd559b1 (fix: desacople frankfurter + fix plotly fillcolor + docker estable)
=======
>>>>>>> b8a43b0 (chore: remove data folder from repo)
