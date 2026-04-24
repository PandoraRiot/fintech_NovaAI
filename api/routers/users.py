"""
api/routers/users.py — Endpoints de predicción e insights por usuario
GET  /api/v1/users/{user_id}          → Perfil 360° + segmento ML
GET  /api/v1/users/{user_id}/insights → Insights personalizados
POST /api/v1/users/{user_id}/ask      → Consulta al agente IA
GET  /api/v1/users                    → Lista de usuarios disponibles
"""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
import pandas as pd
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from api.schemas import (
    PredictResponse, UserProfile, SegmentInfo, RiskFlags,
    UserInsightsResponse, InsightItem, AgentRequest, AgentResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Usuarios & Predicciones"])


def _load_gold() -> pd.DataFrame:
    """Carga el Gold layer desde Parquet. Lanza 503 si no existe."""
    from config import GOLD_FILE
    if not GOLD_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gold layer no disponible. Ejecuta primero POST /api/v1/pipeline/run",
        )
    return pd.read_parquet(GOLD_FILE)


def _get_user(user_id: str, gold: pd.DataFrame) -> pd.Series:
    """Busca un usuario en Gold. Lanza 404 si no existe."""
    rows = gold[gold["userId"] == user_id]
    if rows.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario '{user_id}' no encontrado. Verifica el ID.",
        )
    return rows.iloc[0]


def _row_to_profile(user: pd.Series) -> UserProfile:
    """Convierte una fila Gold en el schema UserProfile."""
    return UserProfile(
        user_id=str(user.get("userId", "")),
        name=str(user.get("name", "")) or None,
        age=float(user.get("age", 0)) or None,
        city=str(user.get("city", "")) or None,
        country=str(user.get("country", "")) or None,
        segment=str(user.get("segment", "")) or None,
        total_spent=float(user.get("total_spent", 0)),
        avg_transaction=float(user.get("avg_transaction", 0)),
        n_transactions=int(user.get("n_transactions", 0)),
        fail_ratio=float(user.get("fail_ratio", 0)),
        current_balance=float(user.get("current_balance", 0)),
        avg_balance=float(user.get("avg_balance", 0)),
        cluster=int(user.get("cluster", 0)),
        segment_info=SegmentInfo(
            icon=str(user.get("segment_icon", "👤")),
            name=str(user.get("segment_name", "Desconocido")),
            color=str(user.get("segment_color", "#6B7280")),
        ),
        risk_flags=RiskFlags(
            is_high_value=bool(user.get("is_high_value", 0)),
            is_low_balance=bool(user.get("is_low_balance", 0)),
            is_high_risk=bool(user.get("is_high_risk", 0)),
            is_dormant=bool(user.get("is_dormant", 0)),
            financial_stress=bool(user.get("financial_stress", 0)),
        ),
        peak_hour=int(user.get("peak_hour", 0)) if user.get("peak_hour") is not None else None,
        preferred_channel=str(user.get("preferred_channel", "")) or None,
        preferred_device=str(user.get("preferred_device", "")) or None,
    )


@router.get(
    "",
    summary="Listar todos los usuarios",
    description="Retorna la lista de IDs de usuarios disponibles en el Gold layer.",
)
async def list_users() -> dict:
    gold = _load_gold()
    users = gold[["userId", "name", "segment_name", "total_spent"]].copy()
    users["total_spent"] = users["total_spent"].round(0)
    return {
        "count": len(users),
        "users": users.to_dict(orient="records"),
    }


@router.get(
    "/{user_id}",
    response_model=PredictResponse,
    summary="Perfil 360° + predicción ML de un usuario",
    description="""
    Retorna el perfil completo del usuario enriquecido con:
    - **Métricas financieras** (gasto, balance, actividad)
    - **Segmento KMeans** (Premium | Estándar | Dormido | En Riesgo)
    - **Flags de riesgo** (estrés financiero, balance bajo, etc.)
    - **Insights personalizados** generados por reglas de negocio
    """,
)
async def get_user_predict(user_id: str) -> PredictResponse:
    """Perfil Gold + predicción ML + insights para un usuario."""
    from insights.engine import generate_user_insights

    gold = _load_gold()
    user = _get_user(user_id, gold)
    profile = _row_to_profile(user)

    raw_insights = generate_user_insights(user)
    insights = [InsightItem(**ins) for ins in raw_insights]

    return PredictResponse(
        user_id=user_id,
        profile=profile,
        insights=insights,
    )


@router.get(
    "/{user_id}/insights",
    response_model=UserInsightsResponse,
    summary="Insights personalizados de un usuario",
)
async def get_user_insights(user_id: str) -> UserInsightsResponse:
    """Solo los insights (sin el perfil completo). Útil para widgets externos."""
    from insights.engine import generate_user_insights

    gold = _load_gold()
    user = _get_user(user_id, gold)
    raw_insights = generate_user_insights(user)
    insights = [InsightItem(**ins) for ins in raw_insights]

    return UserInsightsResponse(user_id=user_id, insights=insights)


@router.post(
    "/{user_id}/ask",
    response_model=AgentResponse,
    summary="Consulta al Agente IA sobre un usuario",
    description="""
    Envía una pregunta en lenguaje natural sobre el usuario.
    
    **Prioridad del agente:**
    1. 🦙 **LLaMA 3.2 1B** (vía LLAMA_BASE_URL si está configurado)
    2. 🤖 **Claude API** (vía ANTHROPIC_API_KEY si está configurado)
    3. 📋 **Modo offline** (reglas determinísticas, siempre funciona)
    """,
)
async def ask_agent(user_id: str, request: AgentRequest) -> AgentResponse:
    """Consulta al agente IA con contexto del usuario."""
    from agent.agent import ask_agent as _ask_agent

    gold = _load_gold()
    user = _get_user(user_id, gold)

    answer, new_history, mode = _ask_agent(
        question=request.question,
        user_row=user,
        history=request.history,
    )

    return AgentResponse(
        answer=answer,
        history=new_history,
        mode=mode,
    )
