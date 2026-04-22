# 🏦 FinTech Intelligence Platform

> Plataforma de inteligencia financiera en tiempo (casi) real — MVP nivel producción  
> **Hackathon 2026 · Arquitectura Medallion · ML + LLM + Mobile**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red?logo=streamlit)](https://streamlit.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📌 Descripción del Proyecto

Sistema de inteligencia financiera que procesa **eventos de transacciones bancarias** en tiempo casi real, genera una **visión 360° del usuario**, detecta **patrones y anomalías** mediante ML, y entrega **recomendaciones accionables** via agente IA (LLaMA 3.2 / Claude / offline).

La plataforma incluye una **experiencia web mobile accesible por QR** que permite a cualquier usuario descubrir su perfil financiero en 2 minutos, sin instalar ninguna aplicación.

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NGINX  :80                                   │
│         /api → Backend   /web → Quiz   /dashboard → Streamlit       │
└────────────┬──────────────────┬──────────────────┬─────────────────┘
             │                  │                  │
    ┌────────▼────────┐  ┌──────▼──────┐  ┌───────▼───────┐
    │  FastAPI :8000  │  │ web/quiz    │  │ Streamlit     │
    │  REST API       │  │ (HTML/JS)   │  │ Dashboard     │
    │  + Agente IA    │  │ Mobile-First│  │ :8501         │
    └────────┬────────┘  └─────────────┘  └───────┬───────┘
             │                                     │
    ┌────────▼─────────────────────────────────────▼───────┐
    │              PIPELINE MEDALLION                       │
    │                                                       │
    │  📁 JSON crudo                                        │
    │       │                                               │
    │  🟫 BRONZE ──► Flatten + Parquet                     │
    │       │         + APIs enriquecimiento:               │
    │       │           • Frankfurter (FX rates)            │
    │       │           • ip-api.com (Geo)                  │
    │       │           • RestCountries (metadata)          │
    │  🟪 SILVER ──► Limpieza + Features temporales        │
    │       │         + Flags de negocio                    │
    │       │         + balance_delta, time_slot, hour      │
    │  🟨 GOLD   ──► User 360° (35+ features por usuario)  │
    │               + Agregaciones financieras              │
    │               + Flags de riesgo                       │
    └────────────────────────┬──────────────────────────────┘
                             │
    ┌────────────────────────▼──────────────────────────────┐
    │                  CAPA ML                              │
    │                                                       │
    │  🎯 KMeans k=4          🔍 Isolation Forest           │
    │  • Premium Activo       • 7% contaminación            │
    │  • Activo Estándar      • Features: amount,           │
    │  • Dormido/Ocasional      balance_delta, hour,        │
    │  • En Riesgo              is_failed                   │
    │                                                       │
    │  💡 Motor de Insights (8 tipos, determinístico)       │
    └────────────────────────┬──────────────────────────────┘
                             │
    ┌────────────────────────▼──────────────────────────────┐
    │               AGENTE IA (prioridad cascada)           │
    │                                                       │
    │  1. 🦙 LLaMA 3.2 1B   ← LLAMA_BASE_URL              │
    │  2. 🤖 Claude API     ← ANTHROPIC_API_KEY             │
    │  3. 📋 Reglas offline ← siempre disponible            │
    └───────────────────────────────────────────────────────┘
```

### Stack tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| API | FastAPI 0.111 | REST API + OpenAPI docs |
| Frontend | Streamlit 1.32 | Dashboard analítico |
| Mobile | HTML/JS vanilla | Quiz QR (zero-dependency) |
| Pipeline | Pandas + PyArrow | ETL Medallion |
| ML | scikit-learn | KMeans + Isolation Forest |
| Agente | LLaMA 3.2 / Claude | Lenguaje natural |
| DB | PostgreSQL 16 | Persistencia Gold Layer |
| Cache | Redis 7 | Tasas FX + Geo |
| FX | Frankfurter | Tasas BCE self-hosted |
| Infra | Docker Compose | Orquestación completa |
| Proxy | Nginx | Reverse proxy unificado |

---

## 🚀 Cómo ejecutar

### Prerequisitos
- Docker Desktop ≥ 24 (con Compose v2)
- 4GB RAM disponible
- Puertos libres: 80, 8000, 8080, 8501, 5432, 6379

### 1. Clonar y configurar

```bash
git clone https://github.com/tu-usuario/fintech-intelligence-mvp.git
cd fintech-intelligence-mvp

# Configurar variables de entorno
cp .env.example .env
```

Editar `.env` — mínimo requerido para el demo:

```env
# Si tienes cluster LLaMA asignado:
LLAMA_BASE_URL=http://tu-cluster:8080
LLAMA_MODEL=llama3.2:1b

# Si tienes API key de Claude (fallback):
ANTHROPIC_API_KEY=sk-ant-...

# Si no tienes ninguna → funciona en modo offline con reglas determinísticas
```

### 2. Levantar el sistema

```bash
# Primera vez (construye imágenes)
docker compose up --build

# Veces siguientes (en background)
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f backend
docker compose logs -f frontend
```

### 3. Acceder

| Servicio | URL | Descripción |
|---------|-----|-------------|
| 🏠 Landing / Quiz QR | http://localhost/web/ | Experiencia mobile principal |
| 📊 Dashboard | http://localhost:8501 | Análisis completo |
| 📚 API Docs | http://localhost:8000/docs | Swagger UI interactivo |
| 🔁 ReDoc | http://localhost:8000/redoc | Documentación alternativa |
| 💰 Tasas FX | http://localhost/fx/latest | Frankfurter self-hosted |

### 4. Ejecutar solo en local (sin Docker)

```bash
pip install -r requirements.txt

# Terminal 1 — Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Frontend
streamlit run dashboard/app.py --server.port 8501

# (Opcional) Ejecutar pipeline standalone
python run_pipeline.py
```

### 5. Ejecutar el pipeline via API

```bash
# Ejecutar pipeline completo (Bronze → Silver → Gold → ML)
curl -X POST http://localhost:8000/api/v1/pipeline/run

# Ver estado del pipeline
curl http://localhost:8000/api/v1/pipeline/status

# Ver usuarios procesados
curl http://localhost:8000/api/v1/users | python -m json.tool
```

---

## 📡 Endpoints de la API

### Eventos

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| `POST` | `/api/v1/events/ingest` | Ingestar eventos financieros |
| `GET` | `/api/v1/events/buffer/status` | Estado del buffer |
| `DELETE` | `/api/v1/events/buffer/flush` | Vaciar buffer |

**Ejemplo — ingestar un evento:**
```bash
curl -X POST http://localhost:8000/api/v1/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "events": [{
      "event_type": "PAYMENT_COMPLETED",
      "event_status": "SUCCESS",
      "userId": "USR_001",
      "amount": 150000,
      "currency": "COP",
      "category": "food",
      "balance_before": 2000000,
      "balance_after": 1850000
    }]
  }'
```

### Pipeline

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| `POST` | `/api/v1/pipeline/run` | Ejecutar Bronze→Silver→Gold→ML |
| `GET` | `/api/v1/pipeline/status` | Estado del último run |

### Usuarios

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| `GET` | `/api/v1/users` | Listar todos los usuarios |
| `GET` | `/api/v1/users/{id}` | Perfil 360° + segmento ML + insights |
| `GET` | `/api/v1/users/{id}/insights` | Solo insights del usuario |
| `POST` | `/api/v1/users/{id}/ask` | Consulta al agente IA |

**Ejemplo — consultar perfil de usuario:**
```bash
curl http://localhost:8000/api/v1/users/USR_001 | python -m json.tool
```

**Ejemplo — consultar al agente:**
```bash
curl -X POST http://localhost:8000/api/v1/users/USR_001/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id": "USR_001", "question": "¿En qué gasto más y cómo puedo mejorar?"}'
```

### Quiz

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| `POST` | `/api/v1/quiz/submit` | Enviar respuestas → perfil financiero |

**Ejemplo:**
```bash
curl -X POST http://localhost:8000/api/v1/quiz/submit \
  -H "Content-Type: application/json" \
  -d '{
    "income_range": "medium",
    "spending_frequency": "frequently",
    "main_category": "food",
    "app_usage": "daily",
    "liquidity_issues": "rarely"
  }'
```

### Sistema

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| `GET` | `/api/v1/health` | Health check completo |

---

## 🧠 Modelos de Machine Learning

### KMeans (Segmentación)

```
Features de entrada (10):
  total_spent, avg_transaction, n_transactions,
  fail_ratio, current_balance, avg_balance,
  unique_days_active, cat_shopping, cat_food, cat_entertainment

Proceso:
  StandardScaler → KMeans(k=4, n_init=10) → Etiquetado por centroide

Clusters resultantes (etiquetado dinámico por score compuesto):
  👑 Premium Activo    → alto gasto + alto balance + bajo fail_ratio
  📈 Activo Estándar   → comportamiento equilibrado
  😴 Dormido/Ocasional → baja frecuencia de transacciones
  ⚠️ En Riesgo        → alto fail_ratio + bajo balance

Métrica de calidad: Silhouette Score (se muestra en dashboard)
```

### Isolation Forest (Anomalías)

```
Features de entrada (4):
  amount, balance_delta, hour, is_failed

Parámetros:
  contamination=0.07 (7% esperado de anomalías)
  n_estimators=100
  random_state=42

Output por transacción:
  is_anomaly: 0/1
  anomaly_score: float (menor = más anómalo)

Uso: detectar transacciones inusuales por monto, hora o patrón de fallos
```

### Motor de Insights (Determinístico)

```
8 tipos de alertas a nivel portafolio:
  1. Alta tasa de fallos sistémica  (>20% usuarios con fail_ratio>30%)
  2. Estrés financiero combinado   (low_balance AND high_risk)
  3. Usuarios dormidos detectados  (>10% con ≤2 transacciones)
  4. Segmento Premium identificado
  5. Categoría de gasto dominante
  6. Hora pico del sistema
  7. Anomalías detectadas
  8. Canal preferido del portafolio

4 tipos de insights a nivel usuario:
  1. Estrés financiero personal
  2. Usuario de alto valor (VIP)
  3. Usuario dormido
  4. Categoría de gasto principal
```

---

## 🦙 Configuración del Agente LLaMA 3.2

El agente usa un sistema de **prioridad en cascada**:

```
LLAMA_BASE_URL configurada?
  ├── SÍ → Intenta LLaMA 3.2 vía OpenAI-compatible API
  │         ├── Éxito → responde con LLaMA ✅
  │         └── Error → siguiente prioridad ↓
  │
ANTHROPIC_API_KEY configurada?
  ├── SÍ → Intenta Claude API
  │         ├── Éxito → responde con Claude ✅
  │         └── Error → siguiente prioridad ↓
  │
SIEMPRE disponible → Modo offline (reglas determinísticas) ✅
```

### Conectar al cluster LLaMA asignado

El modelo a usar es:
```
deqing/fone-llama-3.2-1B-fineweb-sample-100BT-fone3d-hybrid-tile-v4
```
URL: https://huggingface.co/deqing/fone-llama-3.2-1B-fineweb-sample-100BT-fone3d-hybrid-tile-v4

**Si el cluster usa vLLM** (escenario más común):
```env
LLAMA_BASE_URL=http://<IP-DEL-CLUSTER>:<PUERTO>
LLAMA_MODEL=deqing/fone-llama-3.2-1B-fineweb-sample-100BT-fone3d-hybrid-tile-v4
```

**Si el cluster usa Ollama:**
```env
LLAMA_BASE_URL=http://<IP-DEL-CLUSTER>:11434
LLAMA_MODEL=llama3.2:1b
```

**Si el cluster usa LM Studio:**
```env
LLAMA_BASE_URL=http://<IP-DEL-CLUSTER>:1234
LLAMA_MODEL=llama-3.2-1b
```

El agente hace `POST {LLAMA_BASE_URL}/v1/chat/completions` en formato OpenAI Chat — el endpoint estándar de cualquier runtime compatible.

### Verificar que el cluster responde

```bash
# Test manual del endpoint LLaMA
curl -X POST http://TU-CLUSTER:PUERTO/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:1b",
    "messages": [{"role": "user", "content": "Hola, responde en español."}],
    "max_tokens": 100
  }'

# Si responde con JSON {"choices": [...]} → está listo para conectar
```

---

## 🔄 Flujo de Datos End-to-End

```
QUIZ MOBILE (5 preguntas)
     │
     ▼ POST /api/v1/quiz/submit
     │
     ├── income_range      → monthly_income (COP)
     ├── spending_frequency → n_transactions
     ├── main_category     → category distribution
     ├── app_usage         → channel, device, days_active
     └── liquidity_issues  → fail_rate, min_balance_factor
     │
     ▼ generate_synthetic_events()
     │   Genera N eventos coherentes con timestamps del último mes
     │   Incluye: PAYMENT_COMPLETED, PAYMENT_FAILED, MONEY_ADDED
     │
     ▼ PIPELINE MEDALLION (mini-run)
     │   Bronze → Silver → Gold → KMeans
     │
     ▼ QuizResult
     │   profile_name, segment_icon, risk_level,
     │   strengths[], opportunities[], recommendations[]
     │
     ▼ UI RESULT
         Perfil financiero personalizado con CTA
```

---

## 📁 Estructura del Proyecto

```
fintech-intelligence-mvp/
│
├── api/                      # FastAPI backend
│   ├── main.py               # App principal + middlewares
│   ├── schemas.py            # Pydantic v2 — contratos de datos
│   └── routers/
│       ├── events.py         # POST /events/ingest
│       ├── pipeline.py       # POST /pipeline/run
│       ├── users.py          # GET /users/{id} + agente
│       └── quiz.py           # POST /quiz/submit
│
├── pipeline/                 # ETL Medallion
│   ├── bronze.py             # JSON → Parquet (flatten)
│   ├── silver.py             # Limpieza + features temporales
│   └── gold.py               # User 360° (35+ features)
│
├── models/                   # Machine Learning
│   ├── clustering.py         # KMeans k=4 + etiquetado
│   └── anomaly.py            # Isolation Forest
│
├── insights/
│   └── engine.py             # Motor de insights (8 tipos)
│
├── agent/
│   └── agent.py              # LLaMA → Claude → Offline
│
├── enrichment/
│   └── apis.py               # Frankfurter + ip-api + RestCountries
│
├── dashboard/
│   └── app.py                # Streamlit (5 secciones)
│
├── web/
│   └── index.html            # Quiz Mobile (HTML/JS puro)
│
├── utils/
│   └── db.py                 # PostgreSQL (graceful degradation)
│
├── docker/
│   ├── nginx.conf            # Reverse proxy completo
│   ├── postgres-init.sql     # DDL del Gold Layer
│   └── pgadmin-servers.json  # Config pgAdmin
│
├── data/
│   ├── fintech_events_v4.json # Dataset de eventos
│   ├── bronze/               # Parquet Bronze
│   ├── silver/               # Parquet Silver
│   └── gold/                 # Parquet Gold (user_360.parquet)
│
├── config.py                 # Fuente única de verdad
├── run_pipeline.py           # Script standalone
├── requirements.txt
├── Dockerfile                # Streamlit frontend
├── Dockerfile.backend        # FastAPI backend
├── docker-compose.yml
└── .env.example
```

---

## 🔒 Seguridad

- **Credenciales**: siempre via `.env` — nunca en código
- **Input validation**: Pydantic v2 en todos los endpoints
- **CORS**: configurado en FastAPI (restringir en producción real)
- **Headers de seguridad**: X-Frame-Options, X-Content-Type-Options en nginx
- **Sin almacenamiento de datos sensibles**: el quiz no guarda información personal
- **Graceful degradation**: si una API externa falla, el sistema continúa con fallbacks

---

## 🐛 Troubleshooting

### El pipeline falla al ejecutarse

```bash
# Verificar que el archivo de datos existe
ls -la data/fintech_events_v4.json

# Ver logs detallados
docker compose logs backend | grep -i "error\|warning"
```

### El agente LLaMA no responde

```bash
# 1. Verificar que LLAMA_BASE_URL está configurada
cat .env | grep LLAMA

# 2. Test manual del endpoint
curl -X POST $LLAMA_BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "'$LLAMA_MODEL'", "messages": [{"role":"user","content":"test"}], "max_tokens": 10}'

# 3. Si falla → el agente usa Claude o modo offline automáticamente
```

### El dashboard no carga datos

```bash
# El pipeline debe ejecutarse primero
curl -X POST http://localhost:8000/api/v1/pipeline/run

# O directamente desde Python
python run_pipeline.py
```

### Streamlit no conecta al backend

```bash
# Verificar que ambos servicios están corriendo
docker compose ps

# Reiniciar servicios individuales
docker compose restart backend
docker compose restart frontend
```

---

## 🏆 Diferenciadores Técnicos

1. **Pipeline Medallion real**: no es una simulación — transforma JSON crudo en user profiles con 35+ features en < 1 segundo
2. **Agente IA con cascada de fallback**: LLaMA → Claude → Offline — el sistema NUNCA falla silenciosamente
3. **Motor de insights determinístico**: 8 tipos de alertas sin dependencia de modelos LLM — auditables y explicables
4. **Quiz → eventos sintéticos coherentes**: las respuestas se mapean a features reales del Gold Layer, no a valores arbitrarios
5. **QR + Mobile-first**: experiencia sin instalación, accesible desde cualquier dispositivo en segundos
6. **Sin vendor lock-in**: APIs externas 100% open source (Frankfurter/BCE, ip-api, RestCountries) con fallbacks offline

---

## 📄 Licencia

MIT License — Hackathon 2026
