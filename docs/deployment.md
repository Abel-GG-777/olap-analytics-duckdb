# Cloudflare Pages: despliegue gratuito

El destino del proyecto es **Cloudflare Pages Free**, sirviendo archivos estáticos. DuckDB-Wasm ejecuta las consultas SQL en el navegador. No se necesita Google Cloud, cuenta de facturación, tarjeta, dominio propio, servidor Python ni servicios AWS para el despliegue.

Aplicación desplegada y comprobada: https://olap-analytics-duckdb.pages.dev. [Pruebas Chromium contra producción](https://github.com/Abel-GG-777/olap-analytics-duckdb/actions/runs/41332125428).

## Configuración en Cloudflare

En Workers & Pages → Create application → Continue to Pages → Connect GitHub, selecciona el repositorio `Abel-GG-777/olap-analytics-duckdb`.

En **Set up builds and deployments**:

| Campo | Valor |
|---|---|
| Project name | `olap-analytics-duckdb` |
| Production branch | `main` |
| Framework preset | `None` |
| Build command | `bash scripts/pages-build.sh` |
| Build output directory | `dist` |
| Root directory | Dejar vacío; raíz del repositorio |

En Environment variables, si no se detectan los archivos de versión, usa `NODE_VERSION=22` y `PYTHON_VERSION=3.12`. El repositorio incluye `.node-version` y `.python-version`.

Pulsa **Save and Deploy** después de confirmar que los cambios de la versión web estén publicados en `main`. El proyecto usa únicamente el plan Free y archivos estáticos; no habilites suscripciones de pago, R2 ni funciones de servidor. Cloudflare asignará una URL `pages.dev`; usa la URL que realmente devuelva el despliegue, no una dirección supuesta.

## Qué ejecuta cada cambio

La integración nativa de Cloudflare con GitHub despliega cada push a `main`. Antes de producir `dist`, `scripts/pages-build.sh` crea un entorno Python, instala dependencias, ejecuta Ruff y las pruebas de Python, instala las dependencias JavaScript con `npm ci` y construye la aplicación. Un fallo impide completar ese build de Cloudflare.

GitHub Actions ejecuta además las mismas pruebas, construye la versión estática, instala Chromium y prueba el motor DuckDB-Wasm y los controles del panel. También comprueba la versión FastAPI local dentro de Docker. El artefacto `cloudflare-pages` contiene `dist`.

**Límite de la integración:** el despliegue nativo de Cloudflare y Actions son pipelines independientes. El build de Cloudflare está condicionado a sus verificaciones Python y de construcción; no espera el resultado de las pruebas Chromium ni Docker de Actions. Un fallo de navegador en Actions requiere corregir/revertir el commit. No se presenta esta integración como una promoción condicionada a todos los checks de GitHub.

## Arquitectura de publicación

1. Python genera el modelo estrella reproducible para desarrollo y validación.
2. `python -m scripts.export-web` exporta las cuatro tablas a Parquet; se versiona esa instantánea en `web/data`.
3. El build empaqueta DuckDB-Wasm, workers, estilos, JavaScript y Parquet dentro de `dist`. No usa un CDN externo en tiempo de ejecución.
4. Los binarios WASM se comprimen en gzip para respetar los 25 MiB por archivo de Pages. El navegador descarga y descomprime el bundle compatible mediante `DecompressionStream` antes de iniciar DuckDB.
5. Un Web Worker ejecuta consultas con valores parametrizados. La página presenta el resultado. No se consulta una API remota ni se escribe información de usuarios.

El código npm de DuckDB-Wasm usa una versión fijada; puede incorporar una versión del motor distinta del paquete Python. Parquet es el formato de intercambio y las pruebas concilian los indicadores, en lugar de asumir que el archivo nativo de una versión se abre en otra.

La primera carga descarga aproximadamente 7–9 MiB de motor comprimido más el worker, la aplicación y alrededor de 0,85 MiB de hechos. Esto depende del bundle seleccionado. Se necesita un navegador moderno con WebAssembly y `DecompressionStream`; el cálculo usa memoria y CPU del dispositivo del visitante. No se promete capacidad para datasets arbitrariamente grandes.

## Ejecución y pruebas locales

```bash
npm ci
npm run build
npm run preview
```

Abre http://127.0.0.1:4173. No necesitas Python para ejecutar esta versión con la instantánea ya versionada. Para ejecutar pruebas del navegador:

```bash
npx playwright install chromium
npm run test:web
```

Con una URL de despliegue real, `APP_URL` permite ejecutar las mismas pruebas contra producción. En PowerShell:

```powershell
$env:APP_URL='URL_REAL_DEVUELTA_POR_CLOUDFLARE'
npm.cmd run test:web
```

El smoke Python `scripts/smoke.py` corresponde a la API FastAPI local y no se utiliza contra la publicación estática.

## Costo y límites

El diseño usa solo archivos estáticos del plan Free. No requiere comprar dominio: utiliza `pages.dev`. El plan tiene límites (por ejemplo, builds por mes y tamaño por archivo); no contrates ampliaciones. Si alcanzas un límite, espera su renovación o reduce uso dentro del plan gratuito. Consulta las condiciones vigentes de tu cuenta.

## Fuentes oficiales

- [Configuración de construcción](https://developers.cloudflare.com/pages/configuration/build-configuration/)
- [Límites de Pages](https://developers.cloudflare.com/pages/platform/limits/)
- [DuckDB-Wasm](https://duckdb.org/docs/stable/clients/wasm/overview)

La URL y el resultado real de publicación se registran en `docs/verification.md` al verificarse. Crear el proyecto o terminar un build no demuestra por sí solo que las consultas funcionen en la página pública.
