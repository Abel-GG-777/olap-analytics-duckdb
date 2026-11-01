"""Deterministic demonstration warehouse. One fact row equals one order."""
import random
from datetime import date, timedelta
from pathlib import Path

import duckdb

VERSION = "retail-v1-seed42"


def build(path: Path, count: int = 60000):
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    with duckdb.connect(str(path)) as con:
        con.execute("BEGIN")
        con.execute("CREATE TABLE dim_city(id INTEGER PRIMARY KEY, city VARCHAR)")
        con.executemany("INSERT INTO dim_city VALUES (?, ?)",
                        [(1, "Lima"), (2, "Arequipa"), (3, "Cusco"), (4, "Trujillo")])
        con.execute("CREATE TABLE dim_category(id INTEGER PRIMARY KEY, category VARCHAR)")
        con.executemany("INSERT INTO dim_category VALUES (?, ?)",
                        [(1, "Tecnología"), (2, "Hogar"), (3, "Moda"), (4, "Deportes")])
        con.execute("CREATE TABLE dim_date(date DATE PRIMARY KEY, year INTEGER, quarter INTEGER, month INTEGER)")
        con.execute("""INSERT INTO dim_date
            SELECT d::DATE AS date, year(d)::INTEGER AS year,
            quarter(d)::INTEGER AS quarter, month(d)::INTEGER AS month
            FROM generate_series(DATE '2024-01-01', DATE '2025-12-31', INTERVAL 1 DAY) t(d)""")
        con.execute("""CREATE TABLE fact_sales(
            order_id INTEGER PRIMARY KEY, date DATE REFERENCES dim_date(date),
            city_id INTEGER REFERENCES dim_city(id),
            category_id INTEGER REFERENCES dim_category(id), channel VARCHAR,
            units INTEGER CHECK(units > 0), revenue DECIMAL(14,2), cost DECIMAL(14,2))""")
        rows = []
        for order in range(1, count + 1):
            day = date(2024, 1, 1) + timedelta(days=rng.randrange(731))
            category = rng.randint(1, 4)
            units = rng.randint(1, 5)
            price = [18000, 8500, 5500, 11000][category - 1]
            cents = units * (price + rng.randrange(3000))
            revenue = cents / 100
            cost = round(revenue * rng.randint(50, 85) / 100, 2)
            rows.append((order, day, rng.randint(1, 4), category,
                         rng.choice(["Web", "Tienda"]), units, revenue, cost))
        con.executemany("INSERT INTO fact_sales VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        con.execute("""CREATE VIEW sales AS SELECT f.*, c.city, p.category,
            d.year, d.quarter, d.month FROM fact_sales f
            JOIN dim_city c ON f.city_id=c.id
            JOIN dim_category p ON f.category_id=p.id
            JOIN dim_date d ON f.date=d.date""")
        con.execute("CREATE TABLE metadata(version VARCHAR)")
        con.execute("INSERT INTO metadata VALUES (?)", [VERSION])
        con.execute("COMMIT")


def records(con, sql, params=()):
    result = con.execute(sql, params)
    return [dict(zip([c[0] for c in result.description], row)) for row in result.fetchall()]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=Path("data/retail.duckdb"))
    args = parser.parse_args()
    if args.path.exists():
        parser.error("El archivo ya existe; usa otra ruta para regenerar sin sobrescribir.")
    build(args.path)
    print(f"Warehouse creado: {args.path}")
