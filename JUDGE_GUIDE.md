# Guía para Evaluadores — FinTech NovaAI

## Ejecución del sistema

docker compose up --build

## Accesos

- Dashboard: http://localhost:8501
- API (Swagger): http://localhost:8000/docs
- Web (QR): http://localhost:8000/web/

## Flujo recomendado de prueba

1. Ejecutar pipeline:
POST /api/v1/pipeline/run

2. Listar usuarios:
GET /api/v1/users

3. Consultar perfil:
GET /api/v1/users/{user_id}

4. Probar agente IA:
POST /api/v1/users/{user_id}/ask

## Demo mediante QR

Para acceso desde dispositivos móviles en red local:
http://TU-IP:8000/web/

## Datos

El sistema utiliza datos procesados en:
data/gold/user_360.parquet

## Notas técnicas

- El sistema funciona sin conexión a servicios externos (modo offline)
- Incluye segmentación (KMeans) y detección de anomalías
- El agente IA cuenta con fallback determinístico
