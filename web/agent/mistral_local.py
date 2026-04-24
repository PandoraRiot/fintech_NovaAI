"""
mistral_local.py
────────────────────────────────────────────────────────────
LLM local con Mistral-7B-Instruct optimizado para clúster.

Mejoras aplicadas:
  • Corrección del bug de indentación en model.generate()
  • Cuantización 4-bit (BitsAndBytes) → ~4 GB VRAM en lugar de ~14 GB
  • Flash Attention 2 cuando está disponible (2-4× más rápido)
  • Soporte multi-GPU con device_map="auto"
  • torch.inference_mode() para eliminar gradientes en inferencia
  • KV-cache habilitado
  • Parámetros de generación robustos (repetition_penalty, top_p, top_k)
  • Singleton thread-safe para no cargar el modelo más de una vez
  • Limpieza del output para respuestas limpias
"""

from __future__ import annotations

import gc
import logging
import threading
from typing import Optional

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    GenerationConfig,
    TextStreamer,
)

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────

MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"

GENERATION_DEFAULTS = dict(
    max_new_tokens=512,
    temperature=0.3,
    top_p=0.92,
    top_k=50,
    repetition_penalty=1.15,   # evita loops y repetición de frases
    do_sample=True,
    use_cache=True,             # KV-cache activo → más rápido en secuencias largas
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Singleton thread-safe
# ──────────────────────────────────────────────────────────────

_lock = threading.Lock()
_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForCausalLM] = None


def _detect_dtype() -> torch.dtype:
    """Selecciona el dtype óptimo según hardware disponible."""
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        if props.major >= 8:          # Ampere+ (A100, A10, RTX 30xx…)
            return torch.bfloat16
        return torch.float16
    return torch.float32


def _build_bnb_config() -> Optional[BitsAndBytesConfig]:
    """4-bit NF4 si hay CUDA; None en caso contrario (CPU no soporta bnb)."""
    if not torch.cuda.is_available():
        log.warning("CUDA no disponible – se carga el modelo en CPU (lento).")
        return None

    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",          # NF4 > fp4 en calidad
        bnb_4bit_use_double_quant=True,     # doble cuantización → ahorra ~0.4 GB extra
        bnb_4bit_compute_dtype=_detect_dtype(),
    )


def load_model() -> tuple[AutoTokenizer, AutoModelForCausalLM]:
    """
    Carga tokenizer + modelo una sola vez (patrón singleton).
    Seguro para entornos multi-hilo / multi-worker.
    """
    global _tokenizer, _model

    with _lock:
        if _model is not None:
            return _tokenizer, _model

        log.info("Cargando tokenizer…")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)

        # Mistral no tiene pad_token → usamos eos_token
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            tokenizer.pad_token_id = tokenizer.eos_token_id

        log.info("Cargando modelo (cuantizado 4-bit si hay GPU)…")
        bnb_config = _build_bnb_config()
        dtype = _detect_dtype()

        # Intenta Flash Attention 2; si falla (versión vieja de transformers / sin
        # flash-attn instalado), cae silenciosamente al eager attention.
        attn_impl = "flash_attention_2" if torch.cuda.is_available() else "eager"

        try:
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                quantization_config=bnb_config,
                device_map="auto",          # distribuye automáticamente en GPUs del clúster
                torch_dtype=dtype if bnb_config is None else None,
                attn_implementation=attn_impl,
                trust_remote_code=False,
            )
        except Exception:
            log.warning("Flash Attention 2 no disponible – usando eager attention.")
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                quantization_config=bnb_config,
                device_map="auto",
                torch_dtype=dtype if bnb_config is None else None,
                trust_remote_code=False,
            )

        model.eval()  # desactiva dropout / batch-norm en modo inferencia

        log.info("Modelo listo ✓")
        _tokenizer, _model = tokenizer, model

    return _tokenizer, _model


# ──────────────────────────────────────────────────────────────
# Formateo de prompt (chat template Mistral)
# ──────────────────────────────────────────────────────────────

def build_prompt(
    system: str,
    user_message: str,
    history: Optional[list[dict]] = None,
) -> str:
    """
    Construye el prompt con el chat-template de Mistral:
        <s>[INST] ... [/INST] ... </s><s>[INST] ... [/INST]

    Args:
        system:       Instrucción del sistema (contexto del agente).
        user_message: Mensaje del turno actual del usuario.
        history:      Lista de {'role': 'user'|'assistant', 'content': str}
                      de turnos anteriores (para conversación multi-turno).
    """
    messages = []

    if system:
        # Mistral-Instruct v0.2 no tiene rol 'system' nativo → se prepend al primer user
        first_user = f"[SYSTEM]\n{system}\n[/SYSTEM]\n\n"
    else:
        first_user = ""

    for i, turn in enumerate(history or []):
        content = (first_user + turn["content"]) if i == 0 and turn["role"] == "user" else turn["content"]
        messages.append({"role": turn["role"], "content": content})
        first_user = ""  # solo al primer turno

    user_content = first_user + user_message
    messages.append({"role": "user", "content": user_content})

    tokenizer, _ = load_model()
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    return prompt


# ──────────────────────────────────────────────────────────────
# Generación
# ──────────────────────────────────────────────────────────────

def generate_response(
    prompt: str,
    *,
    max_new_tokens: int = GENERATION_DEFAULTS["max_new_tokens"],
    temperature: float = GENERATION_DEFAULTS["temperature"],
    top_p: float = GENERATION_DEFAULTS["top_p"],
    top_k: int = GENERATION_DEFAULTS["top_k"],
    repetition_penalty: float = GENERATION_DEFAULTS["repetition_penalty"],
    stream: bool = False,
) -> str:
    """
    Genera texto a partir de un prompt ya formateado.

    Args:
        prompt:             Prompt completo (usa build_prompt() para crearlo).
        max_new_tokens:     Tokens máximos a generar.
        temperature:        Creatividad (0.1 = determinista, 1.0 = creativo).
        top_p:              Nucleus sampling.
        top_k:              Top-K sampling.
        repetition_penalty: >1 penaliza repeticiones.
        stream:             Si True, imprime tokens en tiempo real (útil en CLI).

    Returns:
        Texto generado (sin el prompt original).
    """
    tokenizer, model = load_model()

    # Determina el device del modelo (primer parámetro disponible)
    device = next(model.parameters()).device

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=3072,            # contexto extendido (v0.2 soporta 32k, pero RAM/VRAM limita)
        padding=False,
    ).to(device)

    gen_config = GenerationConfig(
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        repetition_penalty=repetition_penalty,
        do_sample=temperature > 0,
        use_cache=True,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id,
    )

    streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True) if stream else None

    with torch.inference_mode():  # más eficiente que torch.no_grad() en inferencia
        output_ids = model.generate(
            **inputs,
            generation_config=gen_config,
            streamer=streamer,
        )

    # Decodifica solo los tokens nuevos (excluye el prompt)
    new_token_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
    response = tokenizer.decode(new_token_ids, skip_special_tokens=True).strip()

    return response


# ──────────────────────────────────────────────────────────────
# API de alto nivel (compatible con agent.agent)
# ──────────────────────────────────────────────────────────────

def ask(
    user_message: str,
    *,
    system: str = "",
    history: Optional[list[dict]] = None,
    **gen_kwargs,
) -> str:
    """
    Interfaz simplificada para el agente.

    Ejemplo:
        response = ask(
            "¿Estoy en riesgo financiero?",
            system="Eres un asesor financiero…",
            history=[{"role": "user", "content": "Hola"}, {"role": "assistant", "content": "¡Hola!"}]
        )
    """
    prompt = build_prompt(system=system, user_message=user_message, history=history)
    return generate_response(prompt, **gen_kwargs)


def clear_cache() -> None:
    """Libera la VRAM del modelo (útil entre jobs en clúster con un solo nodo)."""
    global _tokenizer, _model
    with _lock:
        if _model is not None:
            del _model
            _model = None
            _tokenizer = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            log.info("Modelo descargado de memoria.")


# ──────────────────────────────────────────────────────────────
# Smoke-test rápido
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    respuesta = ask(
        "¿Cuál es la diferencia entre ahorro e inversión? Sé breve.",
        system="Eres un asesor financiero amigable que responde en español.",
        temperature=0.3,
        max_new_tokens=200,
    )
    print("\n── Respuesta ──")
    print(respuesta)
