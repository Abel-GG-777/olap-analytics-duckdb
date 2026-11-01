# Verificación y pendientes

Fecha: 2026-11-01 (America/Lima).

## Comprobado localmente

- Repositorio remoto: `https://github.com/Abel-GG-777/olap-analytics-duckdb`; la API pública de GitHub informa `visibility=public`, rama predeterminada `main`.
- Python 3.12; DuckDB 2.0.0; FastAPI 0.162.0; pytest 9.2.0.
- `python -m pytest -q`: **15 passed**. Incluye la integridad de la instantánea Parquet y una regresión del reintento HTTP durante el arranque del contenedor. Advertencia de deprecación de Starlette sobre el adaptador httpx de TestClient; no impide las pruebas.
- `python -m ruff check app tests scripts`: sin errores.
- `node --check app/static/app.js`: sin errores de sintaxis.
- Generador completo ejecutado: 60 000 pedidos, 180 281 unidades, ingresos 22 156 502,75 PEN, utilidad 7 189 634,09 PEN, ticket 369,2750458333333 PEN, margen 32,44931824811567 %; 24 períodos mensuales.
- Servidor Uvicorn iniciado; `scripts/smoke.py http://127.0.0.1:8080` comprobó salud, página principal y filtro Lima (15 050 pedidos).
- `npm run build`: construcción estática completada. El mayor archivo generado es el bundle WASM MVP comprimido, de aproximadamente 8,33 MiB, por debajo de 25 MiB. La tabla de hechos Parquet ocupa aproximadamente 0,85 MiB.

## Límites de esta verificación

- La automatización del navegador del escritorio no obtuvo autorización a tiempo. Las pruebas Chromium automatizadas se incorporaron al workflow remoto; su resultado se registra por separado.
- Docker no está disponible localmente; la construcción y el smoke del contenedor se ejecutan en el workflow de GitHub. El resultado remoto se registra más abajo.
- Cloudflare Pages: conexión GitHub autorizada por el propietario y pantalla de configuración abierta. Todavía no se ha confirmado un build ni una URL pública de Cloudflare.
- Google Cloud Run fue descartado por el requisito de no pagar; se eliminaron el script y el job de despliegue GCP.
- Dev.to: artículo actualizado para DuckDB-Wasm y Cloudflare en `docs/devto.md`, no publicado. El propietario lo publicará manualmente; no se solicita credencial.
- No se ejecutó un benchmark ni una prueba de carga. No se afirma latencia ni capacidad de producción.

## Historial remoto: versión inicial de API local

- Código publicado en `main`, commit `1678ac114e41b55187ee46361320e4a047ef1686`.
- [Run verificado de GitHub Actions](https://github.com/Abel-GG-777/olap-analytics-duckdb/actions/runs/41328624294): estado `completed`, conclusión `success`.
- Job `verify`: exitoso, incluidas las 14 pruebas, Ruff, sintaxis JavaScript, construcción de la imagen Docker y smoke HTTP del contenedor de producción en Linux.
- Job `deploy`: `skipped` por ausencia de configuración GCP. El éxito global del run no se presenta como un despliegue.
- Los primeros runs detectaron una importación de pytest y un reinicio de conexión durante el arranque; se corrigieron antes de este run exitoso.
