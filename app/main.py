import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.warehouse import VERSION, build, records

STATIC = Path(__file__).parent / "static"


def create_app(db_path=None):
    path = Path(db_path or os.getenv("DUCKDB_PATH", "data/retail.duckdb"))

    @asynccontextmanager
    async def lifespan(app):
        if not path.exists():
            build(path)
        with duckdb.connect(str(path), read_only=True) as con:
            if con.execute("SELECT version FROM metadata").fetchone()[0] != VERSION:
                raise RuntimeError("Versión del dataset incompatible")
        yield

    app = FastAPI(title="Andes Analytics · OLAP", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(STATIC / "index.html")

    @app.get("/health")
    def health():
        with duckdb.connect(str(path), read_only=True) as con:
            count = con.execute("SELECT count(*) FROM fact_sales").fetchone()[0]
        return {"status": "ok", "orders": count, "dataset": VERSION}

    @app.get("/api/analytics")
    def analytics(
        start: date = date(2024, 1, 1), end: date = date(2025, 12, 31),
        city: Literal["Lima", "Arequipa", "Cusco", "Trujillo"] | None = None,
        category: Literal["Tecnología", "Hogar", "Moda", "Deportes"] | None = None,
        channel: Literal["Web", "Tienda"] | None = None,
        dimension: Literal["city", "category", "channel"] = "city",
        grain: Literal["month", "quarter", "year"] = "month",
        limit: int = Query(10, ge=1, le=20),
    ):
        if start > end:
            raise HTTPException(422, "La fecha inicial debe ser anterior a la final")
        where = "date BETWEEN ? AND ?"
        params = [start, end]
        for name, value in [("city", city), ("category", category), ("channel", channel)]:
            if value:
                where += f" AND {name} = ?"
                params.append(value)
        # Identifiers only come from Literal allowlists; values are bound parameters.
        with duckdb.connect(str(path), read_only=True) as con:
            base = f"FROM sales WHERE {where}"
            summary = records(con, f"""SELECT count(*) AS orders,
                coalesce(sum(units),0) AS units, coalesce(sum(revenue),0) AS revenue,
                coalesce(sum(revenue-cost),0) AS profit,
                coalesce(avg(revenue),0) AS average_order,
                coalesce(100*sum(revenue-cost)/nullif(sum(revenue),0),0) AS margin {base}""", params)[0]
            groups = records(con, f"""SELECT {dimension} AS label, count(*) AS orders,
                sum(revenue) AS revenue, sum(revenue-cost) AS profit {base}
                GROUP BY {dimension} ORDER BY revenue DESC, label LIMIT ?""", [*params, limit])
            trend = records(con, f"""WITH periods AS (
                SELECT date_trunc('{grain}',date)::DATE AS period, sum(revenue) AS revenue
                {base} GROUP BY 1)
                SELECT *, revenue-lag(revenue) OVER (ORDER BY period) AS change
                FROM periods ORDER BY period""", params)
            cube = records(con, f"""SELECT city, category,
                grouping(city) AS city_total, grouping(category) AS category_total,
                sum(revenue) AS revenue {base}
                GROUP BY ROLLUP(city, category) ORDER BY city NULLS LAST, category NULLS LAST""", params)
        return {"summary": summary, "groups": groups, "trend": trend, "rollup": cube,
                "dataset": VERSION, "currency": "PEN"}

    return app


app = create_app()
