# 🏦 FinTech Intelligence Platform

> Plataforma de inteligencia financiera en tiempo (casi) real — MVP nivel producción  
**Hackathon 2026 · Arquitectura Medallion · ML + LLM + Mobile**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com/) [![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red?logo=streamlit)](https://streamlit.io/) [![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com/) 


## 📌 Descripción del Proyecto

Sistema de inteligencia financiera que procesa **eventos de transacciones bancarias** en tiempo casi real, genera una **visión 360° del usuario**, detecta **patrones y anomalías** mediante ML, y entrega **recomendaciones accionables**  multiagente IA (Mistral 7b, LLaMA 3.2 / Claude / offline con los datos de arquitectura Medallion).

La plataforma incluye una **experiencia web mobile accesible por QR** que permite a cualquier usuario descubrir su perfil financiero en 2 minutos, sin instalar ninguna aplicación y con tan solo un click.


Ver demo: [Cuestionario](https://www.youtube.com/watch?v=y2cK__h5rs0)

Ver demo: [MVP Fintech NovaIA](https://www.youtube.com/watch?v=Ke1hc862LAs&t=1s)


## 👥 Distribución del Trabajo

Líder de proyecto: Erika Alexandra García Barrios | Creadora de repositorio.

| Ejecuciones | Integrantes |
| - | - |
| Isolation Forest | Andrés Medina (Ing Biomédica) |
| **Modelos LLM (Mistral7b, Llama, Claude)** | Erika Alexandra García Barrios (Ing de Software) |
| Clusterización (Docker) , Postgrest,  Nginx | Julián Andrés Gomez Rueda (Ing de Software) |
| Dashboard | Erika Alexandra García Barrios (Ing de Software) |
| Kmeans  | Andrés Medina (Ing Biomédica) |
| QR interactivo | Erika Alexandra García Barrios (Ing de Software) |
| Arquitectura  | Trabajo en equipo |
| Montaje | Trabajo en equipo |
| Planeación y ejecución | Trabajo en equipo colaborativo |
| Documentación | Erika Alexandra García Barrios (Ing de Software) |





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
    │       │         + balance\_delta, time\_slot, hour      │  
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
    │  • Dormido/Ocasional      balance\_delta, hour,        │  
    │  • En Riesgo              is\_failed                   │  
    │                                                       │  
    │  💡 Motor de Insights (8 tipos, determinístico)       │  
    └────────────────────────┬──────────────────────────────┘  
                             │  
    ┌────────────────────────▼──────────────────────────────┐  
    │               AGENTE IA (prioridad cascada)           │  
    │  1. 🌼 Mistral 7b     ← MISTRAL\_API\_KEY                                                │  
    │  2. 🦙 LLaMA 3.2 1B   ← LLAMA\_BASE\_URL              │  
    │  3. 🤖 Claude API     ← ANTHROPIC\_API\_KEY             │  
    │  4. 📋 Reglas offline ← siempre disponible            │  
    └───────────────────────────────────────────────────────┘
```

### Stack tecnológico

| Capa | Tecnología | Rol |
| - | - | - |
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



## 🚀 Cómo ejecutar

### Prerequisitos

- Docker Desktop ≥ 24 (con Compose v2)

- 4GB RAM disponible

- Puertos libres: 80, 8000, 8080, 8501, 5432, 6379

### 1. Clonar y configurar

```
git clone https://github.com/tu-usuario/fintech-intelligence-mvp.git  
cd fintech-intelligence-mvp  
  
\# Configurar variables de entorno  
cp .env.example .env
```

Editar `.env` — mínimo requerido para el demo:

```
\# Si tienes cluster LLaMA asignado:  
LLAMA\_BASE\_URL=http://tu-cluster:8080  
LLAMA\_MODEL=llama3.2:1b  
  
\# Si tienes API key de Claude (fallback):  
ANTHROPIC\_API\_KEY=sk-ant-...  
  
\# Si no tienes ninguna → funciona en modo offline con reglas determinísticas
```

### 2. Levantar el sistema

```
\# Primera vez (construye imágenes)  
docker compose up --build  
  
\# Veces siguientes (en background)  
docker compose up -d  
  
\# Ver logs en tiempo real  
docker compose logs -f backend  
docker compose logs -f frontend
```

### 3. Acceder

| Servicio | URL | Descripción |
| - | - | - |
| 🏠 Landing / Quiz QR | http://localhost/web/ | Experiencia mobile principal |
| 📊 Dashboard | http://localhost:8501 | Análisis completo |
| 📚 API Docs | http://localhost:8000/docs | Swagger UI interactivo |
| 🔁 ReDoc | http://localhost:8000/redoc | Documentación alternativa |
| 💰 Tasas FX | http://localhost/fx/latest | Frankfurter self-hosted |


### 4. Ejecutar solo en local (sin Docker)

```
pip install -r requirements.txt  
  
\# Terminal 1 — Backend  
uvicorn api.main:app --reload --port 8000  
  
\# Terminal 2 — Frontend  
streamlit run dashboard/app.py --server.port 8501  
  
\# (Opcional) Ejecutar pipeline standalone  
python run\_pipeline.py
```

### 5. Ejecutar el pipeline via API

```
\# Ejecutar pipeline completo (Bronze → Silver → Gold → ML)  
curl -X POST http://localhost:8000/api/v1/pipeline/run  
  
\# Ver estado del pipeline  
curl http://localhost:8000/api/v1/pipeline/status  
  
\# Ver usuarios procesados  
curl http://localhost:8000/api/v1/users | python -m json.tool
```


## 📡 Endpoints de la API

### Eventos

| Método | Endpoint | Descripción |
| - | - | - |
| `POST` | `/api/v1/events/ingest` | Ingestar eventos financieros |
| `GET` | `/api/v1/events/buffer/status` | Estado del buffer |
| `DELETE` | `/api/v1/events/buffer/flush` | Vaciar buffer |


**Ejemplo — ingestar un evento:**

```
curl -X POST http://localhost:8000/api/v1/events/ingest \\  
  -H "Content-Type: application/json" \\  
  -d '\{  
    "events": \[\{  
      "event\_type": "PAYMENT\_COMPLETED",  
      "event\_status": "SUCCESS",  
      "userId": "USR\_001",  
      "amount": 150000,  
      "currency": "COP",  
      "category": "food",  
      "balance\_before": 2000000,  
      "balance\_after": 1850000  
    \}\]  
  \}'
```

### Pipeline

| Método | Endpoint | Descripción |
| - | - | - |
| `POST` | `/api/v1/pipeline/run` | Ejecutar Bronze→Silver→Gold→ML |
| `GET` | `/api/v1/pipeline/status` | Estado del último run |


### Usuarios

| Método | Endpoint | Descripción |
| - | - | - |
| `GET` | `/api/v1/users` | Listar todos los usuarios |
| `GET` | `/api/v1/users/\{id\}` | Perfil 360° + segmento ML + insights |
| `GET` | `/api/v1/users/\{id\}/insights` | Solo insights del usuario |
| `POST` | `/api/v1/users/\{id\}/ask` | Consulta al agente IA |


**Ejemplo — consultar perfil de usuario:**

```
curl http://localhost:8000/api/v1/users/USR\_001 | python -m json.tool
```

**Ejemplo — consultar al agente:**

```
curl -X POST http://localhost:8000/api/v1/users/USR\_001/ask \\  
  -H "Content-Type: application/json" \\  
  -d '\{"user\_id": "USR\_001", "question": "¿En qué gasto más y cómo puedo mejorar?"\}'
```

### Quiz

| Método | Endpoint | Descripción |
| - | - | - |
| `POST` | `/api/v1/quiz/submit` | Enviar respuestas → perfil financiero |


**Ejemplo:**

```
curl -X POST http://localhost:8000/api/v1/quiz/submit \\  
  -H "Content-Type: application/json" \\  
  -d '\{  
    "income\_range": "medium",  
    "spending\_frequency": "frequently",  
    "main\_category": "food",  
    "app\_usage": "daily",  
    "liquidity\_issues": "rarely"  
  \}'
```

### Sistema

| Método | Endpoint | Descripción |
| - | - | - |
| `GET` | `/api/v1/health` | Health check completo |



## 🧠 Modelos de Machine Learning

### KMeans (Segmentación)

```
Features de entrada (10):  
  total\_spent, avg\_transaction, n\_transactions,  
  fail\_ratio, current\_balance, avg\_balance,  
  unique\_days\_active, cat\_shopping, cat\_food, cat\_entertainment  
  
Proceso:  
  StandardScaler → KMeans(k=4, n\_init=10) → Etiquetado por centroide  
  
Clusters resultantes (etiquetado dinámico por score compuesto):  
  👑 Premium Activo    → alto gasto + alto balance + bajo fail\_ratio  
  📈 Activo Estándar   → comportamiento equilibrado  
  😴 Dormido/Ocasional → baja frecuencia de transacciones  
  ⚠️ En Riesgo        → alto fail\_ratio + bajo balance  
  
Métrica de calidad: Silhouette Score (se muestra en dashboard)
```

### Isolation Forest (Anomalías)

```
Features de entrada (4):  
  amount, balance\_delta, hour, is\_failed  
  
Parámetros:  
  contamination=0.07 (7% esperado de anomalías)  
  n\_estimators=100  
  random\_state=42  
  
Output por transacción:  
  is\_anomaly: 0/1  
  anomaly\_score: float (menor = más anómalo)  
  
Uso: detectar transacciones inusuales por monto, hora o patrón de fallos
```

### Motor de Insights (Determinístico)

```
8 tipos de alertas a nivel portafolio:  
  1. Alta tasa de fallos sistémica  (\>20% usuarios con fail\_ratio\>30%)  
  2. Estrés financiero combinado   (low\_balance AND high\_risk)  
  3. Usuarios dormidos detectados  (\>10% con ≤2 transacciones)  
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


## 🦙 Configuración del Agente LLaMA 3.2

El agente usa un sistema de **prioridad en cascada**:

```
LLAMA\_BASE\_URL configurada?  
  ├── SÍ → Intenta LLaMA 3.2 vía OpenAI-compatible API  
  │         ├── Éxito → responde con LLaMA ✅  
  │         └── Error → siguiente prioridad ↓  
  │  
ANTHROPIC\_API\_KEY configurada?  
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

URL: [https://huggingface.co/deqing/fone-llama-3.2-1B-fineweb-sample-100BT-fone3d-hybrid-tile-v4](https://huggingface.co/deqing/fone-llama-3.2-1B-fineweb-sample-100BT-fone3d-hybrid-tile-v4)

**Si el cluster usa vLLM** (escenario más común):

```
LLAMA\_BASE\_URL=http://\<IP-DEL-CLUSTER\>:\<PUERTO\>  
LLAMA\_MODEL=deqing/fone-llama-3.2-1B-fineweb-sample-100BT-fone3d-hybrid-tile-v4
```

**Si el cluster usa Ollama:**

```
LLAMA\_BASE\_URL=http://\<IP-DEL-CLUSTER\>:11434  
LLAMA\_MODEL=llama3.2:1b
```

**Si el cluster usa LM Studio:**

```
LLAMA\_BASE\_URL=http://\<IP-DEL-CLUSTER\>:1234  
LLAMA\_MODEL=llama-3.2-1b
```

El agente hace `POST \{LLAMA\_BASE\_URL\}/v1/chat/completions` en formato OpenAI Chat — el endpoint estándar de cualquier runtime compatible.

### Verificar que el cluster responde

```
\# Test manual del endpoint LLaMA  
curl -X POST http://TU-CLUSTER:PUERTO/v1/chat/completions \\  
  -H "Content-Type: application/json" \\  
  -d '\{  
    "model": "llama3.2:1b",  
    "messages": \[\{"role": "user", "content": "Hola, responde en español."\}\],  
    "max\_tokens": 100  
  \}'  
  
\# Si responde con JSON \{"choices": \[...\]\} → está listo para conectar
```


## 🔄 Flujo de Datos End-to-End

```
QUIZ MOBILE (5 preguntas)  
     │  
     ▼ POST /api/v1/quiz/submit  
     │  
     ├── income\_range      → monthly\_income (COP)  
     ├── spending\_frequency → n\_transactions  
     ├── main\_category     → category distribution  
     ├── app\_usage         → channel, device, days\_active  
     └── liquidity\_issues  → fail\_rate, min\_balance\_factor  
     │  
     ▼ generate\_synthetic\_events()  
     │   Genera N eventos coherentes con timestamps del último mes  
     │   Incluye: PAYMENT\_COMPLETED, PAYMENT\_FAILED, MONEY\_ADDED  
     │  
     ▼ PIPELINE MEDALLION (mini-run)  
     │   Bronze → Silver → Gold → KMeans  
     │  
     ▼ QuizResult  
     │   profile\_name, segment\_icon, risk\_level,  
     │   strengths\[\], opportunities\[\], recommendations\[\]  
     │  
     ▼ UI RESULT  
         Perfil financiero personalizado con CTA
```


## 📁 Estructura del Proyecto

```
fintech_NovaAI/
├── agent/
│   ├── agent.py
│   ├── mistral_local.py
│   └── __init__.py
├── api/
│   ├── main.py
│   ├── schemas.py
│   ├── __init__.py
│   └── routers/
│       ├── events.py
│       ├── pipeline.py
│       ├── quiz.py
│       ├── users.py
│       └── __init__.py
├── config.py
├── dashboard/
│   ├── app.py
│   └── __init__.py
├── docker/
│   ├── entrypoint.sh
│   ├── nginx.conf
│   ├── pgadmin-servers.json
│   └── postgres-init.sql
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.backend
├── enrichment/
│   ├── apis.py
│   └── __init__.py
├── insights/
│   ├── engine.py
│   └── __init__.py
├── models/
│   ├── anomaly.py
│   ├── clustering.py
│   └── __init__.py
├── pipeline/
│   ├── bronze.py
│   ├── silver.py
│   ├── gold.py
│   └── __init__.py
├── utils/
│   ├── db.py
│   └── __init__.py
├── web/
│   ├── index.html
│   └── main.py
├── run_pipeline.py
├── test_agent.py
├── requirements.txt
├── README.md
├── .env.example
├── .dockerignore
└── .gitignore
```


## 🔒 Seguridad

- **Credenciales**: siempre via `.env` — nunca en código

- **Input validation**: Pydantic v2 en todos los endpoints

- **CORS**: configurado en FastAPI (restringir en producción real)

- **Headers de seguridad**: X-Frame-Options, X-Content-Type-Options en nginx

- **Sin almacenamiento de datos sensibles**: el quiz no guarda información personal

- **Graceful degradation**: si una API externa falla, el sistema continúa con fallbacks


## 🐛 Troubleshooting

### El pipeline falla al ejecutarse

```
\# Verificar que el archivo de datos existe  
ls -la data/fintech\_events\_v4.json  
  
\# Ver logs detallados  
docker compose logs backend | grep -i "error\\|warning"
```

### El agente LLaMA no responde

```
\# 1. Verificar que LLAMA\_BASE\_URL está configurada  
cat .env | grep LLAMA  
  
\# 2. Test manual del endpoint  
curl -X POST $LLAMA\_BASE\_URL/v1/chat/completions \\  
  -H "Content-Type: application/json" \\  
  -d '\{"model": "'$LLAMA\_MODEL'", "messages": \[\{"role":"user","content":"test"\}\], "max\_tokens": 10\}'  
  
\# 3. Si falla → el agente usa Mistral, Claude o modo offline automáticamente
```

### El dashboard no carga datos

```
\# El pipeline debe ejecutarse primero  
curl -X POST http://localhost:8000/api/v1/pipeline/run  
  
\# O directamente desde Python  
python run\_pipeline.py
```

### Streamlit no conecta al backend

```
\# Verificar que ambos servicios están corriendo  
docker compose ps  
  
\# Reiniciar servicios individuales  
docker compose restart backend  
docker compose restart frontend
```


## 🏆 Diferenciadores Técnicos

1. **Pipeline Medallion real**: no es una simulación — transforma JSON crudo en user profiles con 35+ features en \< 1 segundo

2. **Agente IA con cascada de fallback**: Mistral →LLaMA → Claude → Offline — el sistema NUNCA falla silenciosamente

3. **Motor de insights determinístico**: 8 tipos de alertas sin dependencia de modelos LLM — auditables y explicables

4. **Quiz → eventos sintéticos coherentes**: las respuestas se mapean a features reales del Gold Layer, no a valores arbitrarios

5. **QR + Mobile-first**: experiencia sin instalación, accesible desde cualquier dispositivo en segundos

6. **Sin vendor lock-in**: APIs externas 100% open source (Frankfurter/BCE, ip-api, RestCountries) con fallbacks offline


Guía para evaluadores, profesores, interesados. 

Disponible en: [Guía y repo](https://github.com/PandoraRiot/fintech_NovaAI/blob/main/JUDGE_GUIDE.md)
