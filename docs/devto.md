---
title: "Construí un laboratorio OLAP con DuckDB: de un modelo estrella a un panel web"
published: false
description: "Mi implementación de un panel analítico con DuckDB, FastAPI, SQL OLAP y un pipeline preparado para Google Cloud Run."
tags: duckdb, python, sql, webdev
---

Quería construir un proyecto individual de datos que pudiera ejecutar, entender y compartir completo. Elegí una pregunta concreta: **¿cómo puedo explorar ingresos y margen de un negocio minorista sin montar un servidor de base de datos dedicado?**

Mi respuesta fue Andes Analytics: un pequeño laboratorio OLAP con DuckDB, una API en FastAPI y un panel web. Publiqué el código en [olap-analytics-duckdb](https://github.com/Abel-GG-777/olap-analytics-duckdb).

El alojamiento que elegí es Google Cloud Run. En esta versión del artículo todavía no tengo un despliegue público verificado: dejé el contenedor y el pipeline preparados, pero necesito habilitar el proyecto de Google Cloud y su identidad de despliegue. Por eso no incluyo un enlace de aplicación que no pueda comprobar. Tampoco utilizo AWS en la arquitectura.

## Primero definí el problema y los datos

Quise responder preguntas habituales: qué ciudad concentra ingresos, qué categoría aporta utilidad y cómo cambia la venta entre meses, trimestres y años. Ese dominio me permitió enseñar operaciones OLAP con indicadores fáciles de interpretar.

Para hacer reproducible el proyecto generé **60 000 pedidos sintéticos**, entre enero de 2024 y diciembre de 2025. Usé cuatro ciudades peruanas —Lima, Arequipa, Cusco y Trujillo—, cuatro categorías y los canales Web y Tienda. La moneda es el sol peruano.

La fuente es mi generador Python, con `random.Random(42)` y versión `retail-v1-seed42`. No son ventas reales ni estadísticas oficiales. Muestreé las dimensiones y las fechas sin diseñar una estacionalidad comercial; no interpreto las diferencias resultantes como evidencia sobre el mercado peruano.

Tomé además una decisión de modelado: cada fila representa un pedido de una sola categoría. No modelé líneas de pedido, devoluciones ni impuestos. Esa simplificación hace que `count(*)` sea un conteo de pedidos válido dentro de este laboratorio.

## Por qué elegí DuckDB

Me interesaba trabajar con SQL analítico dentro de mi aplicación Python. DuckDB me permitió almacenar la instantánea en un archivo, unir dimensiones, agregar medidas y ejecutar ventanas analíticas sin administrar un servicio de base de datos separado.

No elegí el motor a partir de un benchmark propio contra otras bases. Mi objetivo era reducir los componentes de una demostración reproducible y concentrarme en el modelado y las consultas. La [documentación de DuckDB para Python](https://duckdb.org/docs/current/clients/python/overview) fue mi referencia para integrarlo.

También tuve que pensar en la concurrencia: abrí conexiones de solo lectura por solicitud y evité compartir una conexión global entre los hilos de la API. No expuse un editor de SQL arbitrario al público.

## Un modelo estrella pequeño

Organicé el almacén alrededor de `fact_sales`, con ingresos, costo, unidades, fecha, ciudad, categoría y canal. Separé ciudad, categoría y calendario en `dim_city`, `dim_category` y `dim_date`. Dejé el canal como dimensión degenerada en la tabla de hechos.

Una vista llamada `sales` resuelve las uniones para las consultas. Definí claves primarias y foráneas y almacené dinero en `DECIMAL(14,2)`.

El recorrido de una consulta es sencillo:

```text
Navegador → FastAPI → SQL parametrizado → DuckDB → JSON → panel
```

Construí el frontend con HTML, CSS y JavaScript sin framework. Serví la página y la API desde el mismo proceso. Para este alcance, evité añadir una compilación frontend y dependencias externas para dibujar los gráficos.

## Convertí preguntas de negocio en SQL OLAP

Para hacer *slice and dice*, combiné período, ciudad, categoría y canal. Por ejemplo, esta consulta agrupa las ventas web de 2025:

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

Calculé el margen dividiendo utilidad total entre ingresos totales. Promediar los porcentajes de margen de cada pedido habría dado otro indicador.

Para mostrar detalle, subtotal por ciudad y total general usé `ROLLUP`:

```sql
SELECT city, category,
       grouping(city) AS city_total,
       grouping(category) AS category_total,
       sum(revenue) AS revenue
FROM sales
GROUP BY ROLLUP(city, category);
```

Usé `grouping()` para identificar los subtotales explícitamente. Así pude presentar filas de total en el panel sin confundirlas con valores ausentes del dato original.

Para explorar la jerarquía temporal cambié la granularidad entre mes, trimestre y año. Añadí una ventana para comparar períodos:

```sql
WITH periods AS (
  SELECT date_trunc('month', date) AS period,
         sum(revenue) AS revenue
  FROM sales
  GROUP BY 1
)
SELECT *,
       revenue - lag(revenue) OVER (ORDER BY period) AS change
FROM periods
ORDER BY period;
```

Documenté una precisión: la serie omite períodos sin ventas. Por eso `lag` compara con el período anterior presente, que no necesariamente es el mes calendario anterior bajo cualquier filtro. El primer período devuelve `null` para la variación.

## Implementé filtros y estados visibles

En `/api/analytics` acepté fechas, ciudad, categoría, canal, dimensión y granularidad. Envié los valores mediante parámetros SQL y restringí los identificadores dinámicos a listas permitidas. Una dimensión desconocida o un rango invertido recibe un error de validación.

En el panel mostré ingresos, margen bruto, pedidos y ticket promedio, además de una serie temporal, una distribución por dimensión y una tabla de subtotales. Incluí estados de carga, error y selección vacía. Al consultar otra selección oculté los resultados previos para evitar que alguien los confundiera con el nuevo filtro.

## Comprobé los cálculos antes de interpretar el panel

Preparé 13 pruebas automatizadas. Incluí un fixture pequeño donde conozco el resultado: dos pedidos con ingresos de 100 y 50, costos de 60 y 40, utilidad total de 50 y ticket promedio de 75.

Además concilié la suma por ciudades, la serie temporal y el total de `ROLLUP` contra el KPI general. Comprobé filtros combinados, granularidad, datos vacíos, entradas inválidas, generación reproducible y consultas concurrentes.

Al ejecutar el conjunto completo en mi entorno obtuve:

| Medida | Resultado del dataset sintético |
|---|---:|
| Pedidos | 60 000 |
| Unidades | 180 281 |
| Ingresos | S/ 22 156 502,75 |
| Utilidad bruta | S/ 7 189 634,09 |
| Ticket promedio | S/ 369,28 |
| Margen bruto | 32,45 % |

Verifiqué por HTTP el estado del servicio, la página y una selección de Lima con 15 050 pedidos. Esos números describen una ejecución de mi generador; no son resultados de una empresa. No medí un benchmark de rendimiento ni una carga de producción. La revisión visual mediante el navegador quedó sin completar por una limitación de acceso de la sesión.

## Preparé el despliegue automatizado en Google Cloud

Construí un Dockerfile que instala la aplicación y genera el archivo DuckDB durante el build. El contenedor ejecuta un único proceso Uvicorn como usuario sin privilegios. Cada instancia consulta su propia instantánea de solo lectura, por lo que no necesito un disco persistente compartido para esta demo.

Preparé un workflow de GitHub Actions con dos etapas. La primera ejecuta Ruff, pytest, la comprobación de sintaxis JavaScript, la construcción Docker y un smoke test HTTP contra el contenedor. La segunda depende de esas verificaciones y, desde `main`, despliega con `gcloud run deploy --source .`.

Elegí Workload Identity Federation para obtener credenciales temporales, con una condición que restringe propietario, repositorio y rama. Separé las cuentas de despliegue, construcción y ejecución. Después del despliegue, el workflow consulta la URL real y ejecuta otro smoke test.

Dejé la configuración en [la guía de despliegue](https://github.com/Abel-GG-777/olap-analytics-duckdb/blob/main/docs/deployment.md). Si no existe la variable `GCP_PROJECT_ID`, el job de despliegue se omite. Hice explícita esta condición porque una ejecución verde de las pruebas no significa que la aplicación esté publicada.

El paso pendiente es configurar un proyecto GCP con facturación y permisos, registrar las variables OIDC y ejecutar el primer despliegue. No afirmo haber comprobado Cloud Run mientras ese paso siga pendiente.

## Lo que aprendí

Aprendí que definir el grano del hecho es tan importante como escribir una consulta. Si hubiera mezclado pedidos y líneas de pedido, habría presentado un ticket promedio incorrecto con una interfaz aparentemente convincente.

También aprendí a separar la integridad del modelo, la exactitud del indicador y la disponibilidad del servicio. Una prueba con resultados conocidos me dio evidencia de los cálculos; una petición HTTP me dio evidencia de la API; ninguna de las dos demuestra por sí sola que exista un despliegue público.

Mi siguiente iteración sería incorporar una fuente real con licencia clara, validar su calidad, versionar instantáneas y medir latencia y costo bajo una carga representativa. Para datos privados añadiría autenticación antes de abrir el servicio.

El código, las consultas y las instrucciones para reproducir el laboratorio están en [mi repositorio público](https://github.com/Abel-GG-777/olap-analytics-duckdb). Dejé el estado de verificación documentado para que cualquier lector pueda distinguir lo probado de lo pendiente.
