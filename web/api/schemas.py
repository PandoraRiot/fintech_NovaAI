"""
api/schemas.py — Contratos de datos (Pydantic v2)
Define los modelos de entrada y salida de todos los endpoints.
Validación automática, documentación OpenAPI integrada.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


# ══════════════════════════════════════════════════════════════════════════
# EVENTOS
# ══════════════════════════════════════════════════════════════════════════

class FinancialEvent(BaseModel):
    """Evento financiero crudo tal como llega de la fuente."""
    event_id:         str  = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type:       str  = Field(..., examples=["PAYMENT_COMPLETED"])
    event_status:     str  = Field(..., examples=["SUCCESS", "FAILED"])
    user_id:          str  = Field(..., alias="userId")
    amount:           float
    currency:         str  = Field(default="COP")
    category:         str  = Field(default="services")
    merchant:         Optional[str] = None
    balance_before:   float = 0.0
    balance_after:    float = 0.0
    timestamp:        datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        allowed = {
            "PAYMENT_COMPLETED", "PAYMENT_FAILED",
            "TRANSFER_SENT", "TRANSFER_RECEIVED",
            "WITHDRAWAL", "MONEY_ADDED",
        }
        if v not in allowed:
            raise ValueError(f"event_type debe ser uno de: {allowed}")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v < 0:
            raise ValueError("amount debe ser positivo")
        return v


class IngestRequest(BaseModel):
    """Payload de ingestión: uno o múltiples eventos."""
    events: List[FinancialEvent]

    @field_validator("events")
    @classmethod
    def validate_events_not_empty(cls, v):
        if not v:
            raise ValueError("Se requiere al menos un evento")
        return v


class IngestResponse(BaseModel):
    """Respuesta de ingestión."""
    status:       str
    events_received: int
    message:      str


# ══════════════════════════════════════════════════════════════════════════
# PIPELINE
# ══════════════════════════════════════════════════════════════════════════

class PipelineRunRequest(BaseModel):
    """Parámetros opcionales para ejecutar el pipeline."""
    enable_enrichment: bool = True
    enable_geo:        bool = True
    enable_fx:         bool = True


class PipelineRunResponse(BaseModel):
    """Resultado de una ejecución del pipeline."""
    status:        str
    duration_sec:  float
    n_events:      int
    n_users:       int
    n_anomalies:   int
    silhouette:    float
    timestamp:     datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════
# USUARIO
# ══════════════════════════════════════════════════════════════════════════

class SegmentInfo(BaseModel):
    icon:  str
    name:  str
    color: str


class RiskFlags(BaseModel):
    is_high_value:    bool
    is_low_balance:   bool
    is_high_risk:     bool
    is_dormant:       bool
    financial_stress: bool


class UserProfile(BaseModel):
    """Perfil completo Gold 360° de un usuario."""
    user_id:           str
    name:              Optional[str]
    age:               Optional[float]
    city:              Optional[str]
    country:           Optional[str]
    segment:           Optional[str]
    # Financiero
    total_spent:       float
    avg_transaction:   float
    n_transactions:    int
    fail_ratio:        float
    current_balance:   float
    avg_balance:       float
    # ML
    cluster:           int
    segment_info:      SegmentInfo
    # Riesgo
    risk_flags:        RiskFlags
    # Patrones
    peak_hour:         Optional[int]
    preferred_channel: Optional[str]
    preferred_device:  Optional[str]


class InsightItem(BaseModel):
    titulo:      str
    descripcion: str
    accion:      str
    nivel:       str  # crítico | alto | medio | oportunidad | info
    icono:       Optional[str] = None


class UserInsightsResponse(BaseModel):
    user_id:  str
    insights: List[InsightItem]


class PredictResponse(BaseModel):
    """Predicción + perfil + insights de un usuario."""
    user_id:  str
    profile:  UserProfile
    insights: List[InsightItem]


# ══════════════════════════════════════════════════════════════════════════
# AGENTE
# ══════════════════════════════════════════════════════════════════════════

class AgentRequest(BaseModel):
    user_id:  str
    question: str = Field(..., min_length=3, max_length=500)
    history:  List[Dict[str, str]] = Field(default_factory=list)


class AgentResponse(BaseModel):
    answer:   str
    history:  List[Dict[str, str]]
    mode:     str  # "llama" | "claude" | "offline"


# ══════════════════════════════════════════════════════════════════════════
# QUIZ (Experiencia QR Mobile)
# ══════════════════════════════════════════════════════════════════════════

class QuizAnswers(BaseModel):
    """
    Respuestas del cuestionario interactivo.
    Cada campo acepta claves semánticas que se mapean a valores financieros.
    """
    income_range: str = Field(
        ...,
        description="low | medium | high | premium",
        examples=["medium"],
    )
    spending_frequency: str = Field(
        ...,
        description="rarely | occasionally | frequently | very_frequent",
        examples=["frequently"],
    )
    main_category: str = Field(
        ...,
        description="food | shopping | entertainment | transport | services",
        examples=["food"],
    )
    app_usage: str = Field(
        ...,
        description="none | basic | daily | power_user",
        examples=["daily"],
    )
    liquidity_issues: str = Field(
        ...,
        description="never | rarely | occasionally | frequently",
        examples=["rarely"],
    )

    @field_validator("income_range")
    @classmethod
    def validate_income(cls, v):
        allowed = {"low", "medium", "high", "premium"}
        if v not in allowed:
            raise ValueError(f"income_range debe ser: {allowed}")
        return v

    @field_validator("spending_frequency")
    @classmethod
    def validate_frequency(cls, v):
        allowed = {"rarely", "occasionally", "frequently", "very_frequent"}
        if v not in allowed:
            raise ValueError(f"spending_frequency debe ser: {allowed}")
        return v

    @field_validator("main_category")
    @classmethod
    def validate_category(cls, v):
        allowed = {"food", "shopping", "entertainment", "transport", "services"}
        if v not in allowed:
            raise ValueError(f"main_category debe ser: {allowed}")
        return v

    @field_validator("app_usage")
    @classmethod
    def validate_app_usage(cls, v):
        allowed = {"none", "basic", "daily", "power_user"}
        if v not in allowed:
            raise ValueError(f"app_usage debe ser: {allowed}")
        return v

    @field_validator("liquidity_issues")
    @classmethod
    def validate_liquidity(cls, v):
        allowed = {"never", "rarely", "occasionally", "frequently"}
        if v not in allowed:
            raise ValueError(f"liquidity_issues debe ser: {allowed}")
        return v


class QuizResult(BaseModel):
    """Resultado del quiz: perfil financiero personalizado."""
    user_id:           str
    profile_name:      str    # Nombre del arquetipo (ej: "Explorador Financiero")
    segment_icon:      str
    segment_name:      str
    risk_level:        str    # BAJO | MEDIO | ALTO | CRÍTICO
    risk_color:        str
    summary:           str    # Párrafo descriptivo
    strengths:         List[str]
    opportunities:     List[str]
    recommendations:   List[str]
    metrics:           Dict[str, Any]
    cta_url:           str = "https://github.com/tu-repo/fintech-mvp"
