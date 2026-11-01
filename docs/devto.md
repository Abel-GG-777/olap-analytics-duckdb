---
title: "Construí un panel OLAP con DuckDB que consulta datos en el navegador"
published: false
description: "Mi laboratorio OLAP con modelo estrella, Parquet, DuckDB-Wasm y un despliegue estático gratuito en Cloudflare Pages."
tags: duckdb, python, sql, webdev
---

Quería construir un proyecto individual que cubriera todo el recorrido de una solución analítica: generar datos, modelarlos, escribir SQL, crear una interfaz y preparar su publicación. También tenía una restricción concreta: no quería pagar un servidor ni usar AWS.

Construí **Andes Analytics**, un laboratorio para explorar ventas minoristas sintéticas en Perú. El código está en [mi repositorio público](https://github.com/Abel-GG-777/olap-analytics-duckdb).

La decisión que hizo viable la publicación estática fue ejecutar DuckDB en el navegador con WebAssembly. Conservé además una versión local con FastAPI para estudiar la alternativa con backend. La guía de despliegue usa Cloudflare Pages Free; al escribir esta versión todavía estoy completando la configuración de la cuenta y no tengo una URL pública verificada. No presento una dirección supuesta como una aplicación desplegada.

## Definí un problema que pudiera comprobar

Elegí preguntas de ventas: ¿qué ciudad concentra ingresos?, ¿qué categoría aporta utilidad?, ¿cómo cambia el resultado entre meses, trimestres y años? Son preguntas comprensibles y permiten demostrar operaciones OLAP sin depender de un dominio demasiado especializado.

Generé 60 000 pedidos, entre 2024 y 2025, con cuatro ciudades, cuatro categorías, dos canales y moneda PEN. Usé Python con `random.Random(42)` y versioné la definición como `retail-v1-seed42`.

Los datos son sintéticos. No representan ventas reales ni estadísticas oficiales de Perú. Tampoco diseñé una estacionalidad comercial: muestreé fechas y dimensiones para disponer de un conjunto reproducible, no para inferir comportamiento económico.

Definí el grano como un pedido de una sola categoría. No incluí líneas de pedido, devoluciones, impuestos ni descuentos. Así, `count(*)` representa pedidos dentro de este modelo.

## Por qué elegí DuckDB

Quería trabajar con SQL analítico sin administrar un servidor de base de datos dedicado. DuckDB me permitió unir dimensiones, agregar medidas y utilizar ventanas analíticas desde Python. DuckDB-Wasm llevó esas consultas al navegador del visitante.

No elegí el motor a partir de un benchmark propio contra otros productos. Elegí una herramienta que me permitía construir el laboratorio con pocos componentes y revisar las consultas directamente. Consulté la [documentación de DuckDB-Wasm](https://duckdb.org/docs/stable/clients/wasm/overview) para integrar el motor y su Web Worker.

## Organicé los datos con un modelo estrella

La tabla `fact_sales` contiene pedido, fecha, ciudad, categoría, canal, unidades, ingresos y costo. Separé el calendario, las ciudades y las categorías en `dim_date`, `dim_city` y `dim_category`. Dejé el canal como una dimensión degenerada en el hecho.

En Python definí claves primarias y foráneas y almacené los importes como `DECIMAL(14,2)`. Una vista `sales` resuelve las uniones para las consultas.

Para la versión web exporté las cuatro tablas a Parquet. Preferí ese intercambio a publicar directamente el archivo nativo de DuckDB, porque el paquete Python y el paquete Wasm pueden incorporar versiones distintas del motor.

La arquitectura de publicación quedó así:

```text
Generador Python → Modelo estrella → Parquet versionado
                                      ↓
Cloudflare Pages → Navegador → DuckDB-Wasm en Web Worker → Panel
```

Cloudflare sirve archivos estáticos. El navegador descarga el motor y el dataset, ejecuta SQL y dibuja los resultados. No necesita llamar a una API para resolver cada filtro.

## Traducí las preguntas en SQL OLAP

Implementé filtros combinables por ciudad, categoría, canal y rango de fechas. Esta consulta muestra un ejemplo de *slice and dice*:

```sql
SELECT city, category,
       sum(revenue) AS revenue,
       sum(revenue-cost) AS profit,
       100.0 * sum(revenue-cost)
         / nullif(sum(revenue), 0) AS margin
FROM sales
WHERE date BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'
  AND channel = 'Web'
GROUP BY city, category
ORDER BY revenue DESC;
```

Calculé el margen a partir de los totales. Promediar el porcentaje de cada pedido habría respondido una pregunta diferente.

Para el detalle por ciudad y categoría, el subtotal de cada ciudad y el total general, usé `ROLLUP`:

```sql
SELECT city, category,
       grouping(city) AS city_total,
       grouping(category) AS category_total,
       sum(revenue) AS revenue
FROM sales
GROUP BY ROLLUP(city, category);
```

Usé `grouping()` para identificar los subtotales. En la interfaz puedo etiquetarlos sin confundirlos con un dato faltante.

Para explorar el calendario, cambié la granularidad entre mes, trimestre y año. Añadí una ventana para comparar períodos:

```sql
WITH periods AS (
  SELECT date_trunc('month', date) AS period,
         sum(revenue) AS revenue
  FROM sales
  GROUP BY 1
)
SELECT *, revenue - lag(revenue) OVER (ORDER BY period) AS change
FROM periods
ORDER BY period;
```

Documenté una limitación: la serie omite períodos sin ventas. Por eso `lag` compara con el período anterior presente bajo el filtro, que no siempre es el mes calendario anterior. El primer período devuelve `null`.

## Construí un panel pequeño y comprobable

Usé HTML, CSS y JavaScript para mostrar ingresos, margen bruto, pedidos, ticket promedio, tendencias y una tabla de subtotales. Incluí estados de carga, selección vacía y error.

La primera visita descarga DuckDB-Wasm y los datos. Comprimí los binarios WASM y los descomprimí en el navegador para respetar el límite de tamaño por archivo de Cloudflare Pages. Serví el motor, sus workers y el dataset desde el mismo sitio, sin un CDN externo en tiempo de ejecución.

Las consultas usan parámetros para los valores y listas permitidas para las dimensiones y granularidades. No expuse un editor público de SQL arbitrario. Las operaciones se ejecutan en un Web Worker para separar el trabajo analítico del hilo que dibuja la interfaz.

## Verifiqué indicadores e integridad

Preparé 15 pruebas Python, incluyendo un fixture de dos pedidos con resultados conocidos: ingresos de 150, utilidad de 50 y ticket promedio de 75. Concilié las agregaciones por dimensión, la serie temporal y el total de `ROLLUP` contra el KPI general.

También comprobé entradas inválidas, filtros combinados, períodos vacíos, reproducibilidad, lecturas concurrentes e integridad de la instantánea Parquet. Añadí pruebas Chromium para comprobar las consultas reales de DuckDB-Wasm, los filtros del panel y el ancho de la interfaz móvil; su resultado concreto queda registrado en el informe de verificación del repositorio.

Las dos pruebas de Chromium pasaron en [esta ejecución de Actions](https://github.com/Abel-GG-777/olap-analytics-duckdb/actions/runs/41330796492). Comprobaron los indicadores esperados, el filtro Lima con 15 050 pedidos, los subtotales, las selecciones vacías y una ventana móvil de 390 píxeles sin desbordamiento horizontal del documento.

Con el dataset completo obtuve estos resultados reproducibles:

| Medida | Resultado sintético |
|---|---:|
| Pedidos | 60 000 |
| Unidades | 180 281 |
| Ingresos | S/ 22 156 502,75 |
| Utilidad bruta | S/ 7 189 634,09 |
| Ticket promedio | S/ 369,28 |
| Margen bruto | 32,45 % |

Estos resultados describen mi generador. No son cifras de una empresa ni una evaluación de rendimiento. No hice una prueba de carga y no prometo que el navegador pueda procesar datasets arbitrariamente grandes.

## Preparé la automatización gratuita

Conecté el procedimiento de publicación a la integración de GitHub con Cloudflare Pages. La configuración utiliza `main`, el comando `bash scripts/pages-build.sh` y la salida `dist`.

Ese comando ejecuta las pruebas Python y Ruff antes de construir los archivos estáticos. Por separado, GitHub Actions ejecuta las pruebas Python, construye el sitio, prueba DuckDB-Wasm en Chromium y verifica la versión local con Docker.

Hice explícita una distinción: el despliegue nativo de Cloudflare no espera a que terminen los checks Chromium de Actions. Sí falla si fallan las verificaciones incluidas en su propio comando de construcción. No presento ambos pipelines independientes como un único proceso de promoción condicionado a todos los checks.

Dejé los pasos exactos en [la guía de despliegue](https://github.com/Abel-GG-777/olap-analytics-duckdb/blob/main/docs/deployment.md). La publicación usa el plan gratuito y el dominio `pages.dev`, sin contratar un dominio propio ni activar servicios de pago. Los límites del plan siguen aplicando.

## Lo que aprendí

Aprendí que una restricción de costo puede cambiar la arquitectura. Al mover el motor al navegador eliminé el servidor de consultas del despliegue, pero trasladé al visitante la descarga inicial y el consumo de memoria y CPU.

También aprendí a separar el modelo de su representación de intercambio. El mismo conjunto de datos sirve para una API Python y para DuckDB-Wasm mediante Parquet, mientras las pruebas comprueban que ambos recorridos mantienen los indicadores esperados.

Mi siguiente iteración sería incorporar una fuente real con licencia clara, medir carga inicial y memoria en dispositivos modestos y definir cómo actualizar la instantánea. Para información privada tendría que replantear la distribución: los archivos publicados se descargan al navegador y no deben contener secretos.

El [repositorio](https://github.com/Abel-GG-777/olap-analytics-duckdb) incluye código, consultas, pruebas, ejecución local y un informe que distingue lo comprobado de lo pendiente. Esa separación forma parte del proyecto tanto como el panel.
