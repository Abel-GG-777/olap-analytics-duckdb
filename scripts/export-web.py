"""Export the versioned demonstration snapshot to portable Parquet for WASM."""
import json
from pathlib import Path

import duckdb

from app.warehouse import VERSION

path = Path("web/data")
path.mkdir(parents=True, exist_ok=True)
with duckdb.connect("data/retail.duckdb", read_only=True) as con:
    for table in ["fact_sales", "dim_city", "dim_category", "dim_date"]:
        con.execute(f"COPY {table} TO '{path.as_posix()}/{table}.parquet' (FORMAT PARQUET)")
    count, revenue = con.execute("SELECT count(*),sum(revenue) FROM fact_sales").fetchone()
manifest = {"version": VERSION, "orders": count, "revenue": float(revenue),
            "source": "app/warehouse.py, random.Random(42)", "currency": "PEN"}
(path / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest))
