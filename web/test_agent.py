"""
test_agent.py
────────────────────────────────────────────────────────────
Suite de pruebas para el agente financiero.

Mejoras:
  • Consolidado en un solo archivo (test_agent.py y test_agent_(1).py eran idénticos)
  • Salida con colores ANSI para mayor legibilidad en terminal
  • Reporte de tiempo por consulta
  • Resumen final con conteo de modos usados
  • Manejo de excepciones por caso (no aborta toda la suite)
  • Separación clara de fixtures, preguntas y ejecución
"""

from __future__ import annotations

import time
import traceback

import pandas as pd
from agent.agent import ask_agent


# ──────────────────────────────────────────────────────────────
# Colores ANSI (funcionan en terminales Unix / WSL / macOS)
# ──────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    RED    = "\033[91m"
    GREY   = "\033[90m"


# ──────────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────────

def run_test(user_data: dict, question: str, stats: dict) -> None:
    """
    Ejecuta una consulta al agente e imprime el resultado formateado.

    Args:
        user_data: Diccionario con los datos del usuario.
        question:  Pregunta del usuario.
        stats:     Diccionario mutable para acumular métricas.
    """
    user_row = pd.Series(user_data)

    try:
        t0 = time.perf_counter()
        answer, history, mode = ask_agent(question, user_row)
        elapsed = time.perf_counter() - t0

        stats["ok"] += 1
        stats["modes"][mode] = stats["modes"].get(mode, 0) + 1

        icon = user_data.get("segment_icon", "")
        print(f"\n{'='*60}")
        print(
            f"{C.BOLD}{icon} {user_data['name']}{C.RESET}"
            f"  {C.GREY}│{C.RESET}  Segmento: {C.CYAN}{user_data['segment_name']}{C.RESET}"
            f"  {C.GREY}│{C.RESET}  Modo: {C.YELLOW}{mode}{C.RESET}"
            f"  {C.GREY}│{C.RESET}  ⏱ {elapsed:.2f}s"
        )
        print(f"{C.BOLD}Pregunta:{C.RESET} {question}")
        print(f"\n{C.GREEN}Respuesta:{C.RESET}\n{answer}")
        print("="*60)

    except Exception as exc:
        stats["errors"] += 1
        print(f"\n{C.RED}[ERROR]{C.RESET} {user_data['name']} | {question!r}")
        traceback.print_exc()


# ──────────────────────────────────────────────────────────────
# Fixtures – Perfiles de usuario
# ──────────────────────────────────────────────────────────────

USERS: list[dict] = [

    # ──── 👑 PREMIUM ACTIVO ───────────────────────────────────
    {
        "name": "Carlos",
        "age": 35,
        "city": "Bogotá",
        "country": "Colombia",
        "segment_name": "Premium Activo",
        "segment_icon": "👑",
        "total_spent": 3_000_000,
        "avg_transaction": 150_000,
        "max_transaction": 500_000,
        "current_balance": 1_200_000,
        "avg_balance": 900_000,
        "n_transactions": 50,
        "n_success": 49,
        "n_failed": 1,
        "fail_ratio": 0.02,
        "unique_days_active": 25,
        "peak_hour": 20,
        "preferred_channel": "app",
        "is_high_value": 1,
        "is_low_balance": 0,
        "is_high_risk": 0,
        "financial_stress": 0,
        "is_dormant": 0,
        "cat_food": 800_000,
        "cat_shopping": 1_000_000,
    },

    # ──── 📈 ACTIVO ESTÁNDAR ──────────────────────────────────
    {
        "name": "Laura",
        "age": 28,
        "city": "Cali",
        "country": "Colombia",
        "segment_name": "Activo Estándar",
        "segment_icon": "📈",
        "total_spent": 800_000,
        "avg_transaction": 40_000,
        "max_transaction": 120_000,
        "current_balance": 300_000,
        "avg_balance": 350_000,
        "n_transactions": 30,
        "n_success": 28,
        "n_failed": 2,
        "fail_ratio": 0.06,
        "unique_days_active": 20,
        "peak_hour": 18,
        "preferred_channel": "web",
        "is_high_value": 0,
        "is_low_balance": 0,
        "is_high_risk": 0,
        "financial_stress": 0,
        "is_dormant": 0,
        "cat_transport": 200_000,
        "cat_food": 300_000,
    },

    # ──── 😴 DORMIDO ──────────────────────────────────────────
    {
        "name": "Mateo",
        "age": 40,
        "city": "Barranquilla",
        "country": "Colombia",
        "segment_name": "Dormido",
        "segment_icon": "😴",
        "total_spent": 20_000,
        "avg_transaction": 10_000,
        "max_transaction": 15_000,
        "current_balance": 10_000,
        "avg_balance": 20_000,
        "n_transactions": 2,
        "n_success": 2,
        "n_failed": 0,
        "fail_ratio": 0.0,
        "unique_days_active": 2,
        "peak_hour": 10,
        "preferred_channel": "app",
        "is_high_value": 0,
        "is_low_balance": 1,
        "is_high_risk": 0,
        "financial_stress": 0,
        "is_dormant": 1,
        "cat_food": 20_000,
    },

    # ──── ⚠️ EN RIESGO ────────────────────────────────────────
    {
        "name": "Alexa",
        "age": 22,
        "city": "Medellín",
        "country": "Colombia",
        "segment_name": "En Riesgo",
        "segment_icon": "⚠️",
        "total_spent": 500_000,
        "avg_transaction": 25_000,
        "max_transaction": 100_000,
        "current_balance": 50_000,
        "avg_balance": 120_000,
        "n_transactions": 20,
        "n_success": 15,
        "n_failed": 5,
        "fail_ratio": 0.25,
        "unique_days_active": 10,
        "peak_hour": 22,
        "preferred_channel": "app",
        "is_high_value": 0,
        "is_low_balance": 1,
        "is_high_risk": 1,
        "financial_stress": 1,
        "is_dormant": 0,
        "cat_food": 200_000,
        "cat_transport": 100_000,
    },
]


# ──────────────────────────────────────────────────────────────
# Preguntas de prueba
# ──────────────────────────────────────────────────────────────

QUESTIONS: list[str] = [
    "¿Estoy en riesgo financiero?",
    "¿En qué gasto más dinero?",
    "¿Cómo está mi balance?",
    "Dame un resumen completo",
    "Am I in financial risk?",           # prueba de idioma
]


# ──────────────────────────────────────────────────────────────
# Ejecución
# ──────────────────────────────────────────────────────────────

def main() -> None:
    stats: dict = {"ok": 0, "errors": 0, "modes": {}}
    total = len(USERS) * len(QUESTIONS)

    print(f"\n{C.BOLD}{'─'*60}")
    print(f"  🧪 Test Suite – Agente Financiero")
    print(f"  {total} casos  ({len(USERS)} usuarios × {len(QUESTIONS)} preguntas)")
    print(f"{'─'*60}{C.RESET}\n")

    t_global = time.perf_counter()

    for user in USERS:
        for question in QUESTIONS:
            run_test(user, question, stats)

    elapsed_total = time.perf_counter() - t_global

    # ── Resumen ──────────────────────────────────────────────
    print(f"\n{C.BOLD}{'─'*60}")
    print("  📊 Resumen de la suite")
    print(f"{'─'*60}{C.RESET}")
    print(f"  Total:   {total} casos")
    print(f"  ✅ OK:   {stats['ok']}")
    print(f"  ❌ Err:  {stats['errors']}")
    print(f"  ⏱  Tiempo total: {elapsed_total:.1f}s  ({elapsed_total/total:.2f}s/caso)")
    print(f"\n  Modos usados:")
    for mode, count in sorted(stats["modes"].items(), key=lambda x: -x[1]):
        print(f"    {mode}: {count} veces")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
