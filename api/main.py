"""
api/main.py — FastAPI Application: FinTech Intelligence Platform
═══════════════════════════════════════════════════════════════════

Endpoints:
  POST /api/v1/events/ingest         → Ingestión de eventos
  GET  /api/v1/events/buffer/status  → Estado del buffer
  POST /api/v1/pipeline/run          → Ejecutar pipeline Medallion
  GET  /api/v1/pipeline/status       → Estado del pipeline
  GET  /api/v1/users                 → Listar usuarios
  GET  /api/v1/users/{id}            → Perfil 360° + predicción ML
  GET  /api/v1/users/{id}/insights   → Insights personalizados
  POST /api/v1/users/{id}/ask        → Consulta al Agente IA
  POST /api/v1/quiz/submit           → Quiz financiero → Perfil
  GET  /api/v1/health                → Health check

Docs: http://localhost:8000/docs       (Swagger UI)
      http://localhost:8000/redoc      (ReDoc)
"""
import os
import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import sys

# ── PYTHONPATH ────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fintech.api")

# ── Routers ───────────────────────────────────────────────────────────────
from api.routers.events   import router as events_router
from api.routers.pipeline import router as pipeline_router
from api.routers.users    import router as users_router
from api.routers.quiz     import router as quiz_router


# ── Lifespan: inicialización y teardown ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: valida que los datos existan o avisa que se debe correr el pipeline.
    Shutdown: limpieza de recursos.
    """
    logger.info("🚀 FinTech Intelligence API iniciando...")

    from config import GOLD_FILE, RAW_FILE
    if not RAW_FILE.exists():
        logger.warning(f"⚠️  Archivo de datos no encontrado: {RAW_FILE}")
    elif not GOLD_FILE.exists():
        logger.info(
            "ℹ️  Gold layer no existe aún. Llama a POST /api/v1/pipeline/run "
            "para generar los datos antes de usar los endpoints de usuarios."
        )
    else:
        logger.info(f"✅ Gold layer detectado: {GOLD_FILE}")

    logger.info("✅ API lista en http://localhost:8000")
    logger.info("📚 Docs: http://localhost:8000/docs")
    yield
    logger.info("🛑 FinTech Intelligence API deteniéndose...")


# ── Aplicación ────────────────────────────────────────────────────────────
app = FastAPI(
    title="FinTech Intelligence Platform",
    description="""
## 🏦 FinTech Intelligence Platform — API v1

Plataforma de inteligencia financiera en (casi) tiempo real.

### Arquitectura
- **Bronze → Silver → Gold** (Medallion Pattern)
- **KMeans k=4** (segmentación de usuarios)
- **Isolation Forest** (detección de anomalías)
- **Agente IA** (LLaMA 3.2 / Claude / Offline)

### Flujo típico
1. `POST /api/v1/pipeline/run` → Ejecutar pipeline completo
2. `GET /api/v1/users` → Ver usuarios disponibles
3. `GET /api/v1/users/{id}` → Obtener perfil 360° + segmento ML
4. `POST /api/v1/users/{id}/ask` → Preguntar al agente IA
5. `POST /api/v1/quiz/submit` → Experiencia QR mobile
""",
    version="1.0.0",
    contact={"name": "FinTech Hackathon 2026"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# ── CORS (permite requests desde el frontend web/QR) ─────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # En prod: restringir a dominio específico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Middleware de latencia ────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    elapsed = time.time() - t0
    response.headers["X-Process-Time"] = f"{elapsed*1000:.1f}ms"
    return response


# ── Routers registrados ────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(events_router,   prefix=PREFIX)
app.include_router(pipeline_router, prefix=PREFIX)
app.include_router(users_router,    prefix=PREFIX)
app.include_router(quiz_router,     prefix=PREFIX)

# ── Servir archivos estáticos del frontend web (QR experience) ────────────
web_dir = ROOT / "web"
if web_dir.exists():
    app.mount("/web", StaticFiles(directory=str(web_dir), html=True), name="web")


# ── Endpoints raíz ────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {
        "app": "FinTech Intelligence Platform",
        "version": "1.0.0",
        "status": "running",
        "docs":   "http://localhost:8000/docs",
        "web_ui": "http://localhost:8000/web/",
        "quiz":   "http://localhost:8000/web/#quiz",
    }


@app.get("/api/v1/health", tags=["Sistema"], summary="Health check")
async def health_check():
    """Verifica el estado de todos los componentes del sistema."""
    from config import GOLD_FILE, SILVER_FILE, BRONZE_FILE

    checks = {
        "api":          "ok",
        "bronze_layer": "ok" if BRONZE_FILE.exists() else "missing — run pipeline",
        "silver_layer": "ok" if SILVER_FILE.exists() else "missing — run pipeline",
        "gold_layer":   "ok" if GOLD_FILE.exists()   else "missing — run pipeline",
    }

    # Verificar APIs externas opcionales
    try:
        from enrichment.apis import check_api_health
        api_status = check_api_health()
        checks["external_apis"] = api_status
    except Exception:
        checks["external_apis"] = "check failed"

    overall = "healthy" if all(v == "ok" for k, v in checks.items() if k != "external_apis") else "degraded"

    return {
        "status": overall,
        "checks": checks,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ── Manejadores de error globales ─────────────────────────────────────────
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint no encontrado", "path": str(request.url.path)},
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error(f"Error interno en {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Error interno del servidor", "detail": str(exc)},
    )


# ── Punto de entrada directo ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
