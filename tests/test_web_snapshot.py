import json
from pathlib import Path

import duckdb
import pytest


def test_published_parquet_snapshot():
    root = Path(__file__).resolve().parents[1] / "web" / "data"
    manifest = json.loads((root / "manifest.json").read_text())
    with duckdb.connect() as con:
        for name in ["fact_sales", "dim_city", "dim_category", "dim_date"]:
            filename = (root / f"{name}.parquet").as_posix()
            con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{filename}')")
        count, unique, revenue, profit = con.execute("""SELECT count(*),count(DISTINCT order_id),
            sum(revenue),sum(revenue-cost) FROM fact_sales""").fetchone()
        assert count == unique == manifest["orders"] == 60000
        assert float(revenue) == pytest.approx(22156502.75)
        assert float(profit) == pytest.approx(7189634.09)
        assert float(revenue) == manifest["revenue"]
        assert con.execute("""SELECT count(*) FROM fact_sales f
            JOIN dim_city c ON f.city_id=c.id JOIN dim_category p ON f.category_id=p.id
            JOIN dim_date d ON f.date=d.date""").fetchone()[0] == count
