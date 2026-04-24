"""
api/routers/pipeline.py — Endpoints de orquestación del Pipeline Medallion
POST /api/v1/pipeline/run  → Ejecuta Bronze → Silver → Gold → ML
GET  /api/v1/pipeline/status → Estado del último run

El pipeline es idempotente: puede ejecutarse múltiples veces.
Cada run sobreescribe los Parquet con los datos más recientes.
"""
import time
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from api.schemas import PipelineRunRequest, PipelineRunResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["Pipeline Medallion"])

# Estado del último pipeline run (singleton en memoria)
_last_run: dict = {
    "status": "never_run",
    "timestamp": None,
    "duration_sec": 0.0,
    "n_events": 0,
    "n_users": 0,
    "n_anomalies": 0,
    "silhouette": 0.0,
}
_is_running = False


def _execute_pipeline(enable_enrichment: bool, enable_geo: bool, enable_fx: bool) -> dict:
    """
    Ejecuta el pipeline completo de forma síncrona.
    Bronze → Silver → Gold → KMeans → Isolation Forest
    """
    global _last_run, _is_running
    _is_running = True
    t0 = time.time()

    try:
        from pipeline.bronze   import run_bronze
        from pipeline.silver   import run_silver
        from pipeline.gold     import run_gold
        from models.clustering import run_clustering
        from models.anomaly    import run_anomaly_detection

        bronze = run_bronze(enrich=enable_enrichment)
        silver = run_silver(bronze)
        gold   = run_gold(silver)
        gold, kmeans, scaler, sil, cluster_labels = run_clustering(gold)
        silver_anom, n_anom, top_anom = run_anomaly_detection(silver)

        duration = time.time() - t0
        _last_run = {
            "status":      "completed",
            "timestamp":   datetime.utcnow().isoformat(),
            "duration_sec": round(duration, 2),
            "n_events":    len(silver),
            "n_users":     len(gold),
            "n_anomalies": int(n_anom),
            "silhouette":  round(float(sil), 4),
        }
        logger.info(f"Pipeline completado en {duration:.2f}s — {len(gold)} usuarios")
        return _last_run

    except Exception as e:
        _last_run["status"] = "failed"
        _last_run["error"] = str(e)
        logger.error(f"Pipeline fallido: {e}")
        raise
    finally:
        _is_running = False


@router.post(
    "/run",
    response_model=PipelineRunResponse,
    summary="Ejecutar pipeline Medallion completo",
    description="""
    Ejecuta el pipeline completo:
    1. **Bronze**: Ingestión JSON → Parquet (aplanado)
    2. **Silver**: Limpieza + enriquecimiento APIs + features temporales
    3. **Gold**: Agregación User 360° con 35+ features
    4. **KMeans k=4**: Segmentación de usuarios
    5. **Isolation Forest**: Detección de anomalías

    Tiempo estimado: 0.5–2s en local.
    Idempotente: puede ejecutarse múltiples veces.
    """,
)
async def run_pipeline(
    params: PipelineRunRequest = PipelineRunRequest(),
) -> PipelineRunResponse:
    """
    Dispara el pipeline Medallion completo.
    Bloquea hasta completar (apropiado para MVP, usar BackgroundTasks en prod).
    """
    global _is_running

    if _is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El pipeline ya está en ejecución. Intenta de nuevo en unos segundos.",
        )

    try:
        result = _execute_pipeline(
            enable_enrichment=params.enable_enrichment,
            enable_geo=params.enable_geo,
            enable_fx=params.enable_fx,
        )
        return PipelineRunResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline fallido: {str(e)}",
        )


@router.get(
    "/status",
    summary="Estado del último run del pipeline",
)
async def pipeline_status() -> dict:
    """Retorna metadatos del último run del pipeline."""
    return {
        "is_running": _is_running,
        "last_run": _last_run,
    }
