# Verificación y pendientes

Fecha: 2026-11-01 (America/Lima).

## Comprobado localmente

- Repositorio remoto: `https://github.com/Abel-GG-777/olap-analytics-duckdb`; la API pública de GitHub informa `visibility=public`, rama predeterminada `main`.
- Python 3.12; DuckDB 2.0.0; FastAPI 0.162.0; pytest 9.2.0.
- `python -m pytest -q`: **13 passed**. Advertencia de deprecación de Starlette sobre el adaptador httpx de TestClient; no impide las pruebas.
- `python -m ruff check app tests scripts`: sin errores.
- `node --check app/static/app.js`: sin errores de sintaxis.
- Generador completo ejecutado: 60 000 pedidos, 180 281 unidades, ingresos 22 156 502,75 PEN, utilidad 7 189 634,09 PEN, ticket 369,2750458333333 PEN, margen 32,44931824811567 %; 24 períodos mensuales.
- Servidor Uvicorn iniciado; `scripts/smoke.py http://127.0.0.1:8080` comprobó salud, página principal y filtro Lima (15 050 pedidos).

## Límites de esta verificación

- La automatización del navegador no obtuvo autorización a tiempo. No se completó una inspección visual ni una prueba de interacción en el navegador.
- Docker no está disponible localmente; la construcción y el smoke del contenedor se delegan al workflow de GitHub, cuyo resultado se registrará después del envío.
- Google Cloud Run: no desplegado todavía; faltan proyecto con facturación y configuración OIDC. No se ha verificado el job de despliegue ni una URL pública.
- Dev.to: artículo terminado en `docs/devto.md`, no publicado. Falta sesión accesible o credencial.
- No se ejecutó un benchmark ni una prueba de carga. No se afirma latencia ni capacidad de producción.

## Resultado remoto

Pendiente de registrar el commit y el run de Actions después de publicar el código.
