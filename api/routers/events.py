"""
api/routers/events.py — Endpoint de ingestión de eventos financieros
POST /api/v1/events/ingest

Valida, persiste temporalmente y confirma la recepción de eventos crudos.
En producción, aquí iría la integración con Kafka/Kinesis.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from api.schemas import IngestRequest, IngestResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Ingesta de Eventos"])

# Buffer en memoria para eventos recibidos via API
# En producción: Cola de mensajes (Kafka, SQS, etc.)
_event_buffer: list = []


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingestar eventos financieros",
    description="""
    Recibe uno o múltiples eventos financieros JSON y los añade al buffer
    de procesamiento. Los eventos son validados con Pydantic antes de ser
    aceptados.
    
    En el MVP, los eventos se persisten en un buffer en memoria.
    En producción, este endpoint publicaría a Kafka/Kinesis.
    """,
)
async def ingest_events(payload: IngestRequest) -> IngestResponse:
    """
    Ingesta eventos financieros con validación completa.
    Retorna 202 Accepted cuando los eventos están en cola para procesamiento.
    """
    global _event_buffer

    try:
        # Serializar eventos a dict (ya validados por Pydantic)
        new_events = []
        for evt in payload.events:
            event_dict = evt.model_dump(by_alias=True)
            event_dict["ingested_at"] = datetime.utcnow().isoformat()
            new_events.append(event_dict)

        _event_buffer.extend(new_events)

        logger.info(f"Ingestados {len(new_events)} eventos. Buffer total: {len(_event_buffer)}")

        return IngestResponse(
            status="accepted",
            events_received=len(new_events),
            message=f"{len(new_events)} evento(s) recibido(s) y en cola para procesamiento. "
                    f"Buffer actual: {len(_event_buffer)} eventos.",
        )

    except Exception as e:
        logger.error(f"Error en ingestión: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando eventos: {str(e)}",
        )


@router.get(
    "/buffer/status",
    tags=["Ingesta de Eventos"],
    summary="Estado del buffer de eventos",
)
async def buffer_status() -> dict:
    """Retorna el estado actual del buffer de eventos en memoria."""
    return {
        "buffer_size": len(_event_buffer),
        "status": "ready" if _event_buffer else "empty",
        "message": f"{len(_event_buffer)} evento(s) esperando procesamiento.",
    }


@router.delete(
    "/buffer/flush",
    tags=["Ingesta de Eventos"],
    summary="Vaciar buffer de eventos",
)
async def flush_buffer() -> dict:
    """Vacía el buffer de eventos (útil para testing)."""
    global _event_buffer
    count = len(_event_buffer)
    _event_buffer = []
    return {"flushed": count, "message": f"{count} eventos eliminados del buffer."}
