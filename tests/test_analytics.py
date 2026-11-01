from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.warehouse import build


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    path = tmp_path_factory.mktemp("warehouse") / "test.duckdb"
    build(path, count=1000)
    with TestClient(create_app(path)) as client:
        yield client


def test_health_and_home(client):
    assert client.get("/health").json()["orders"] == 1000
    assert "Andes Analytics" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200


def test_reconciliation(client):
    data = client.get("/api/analytics").json()
    total = data["summary"]["revenue"]
    assert sum(r["revenue"] for r in data["groups"]) == pytest.approx(total)
    assert sum(r["revenue"] for r in data["trend"]) == pytest.approx(total)
    grand = [r for r in data["rollup"] if r["city_total"]]
    assert len(grand) == 1
    assert grand[0]["revenue"] == pytest.approx(total)
    assert data["summary"]["average_order"] == pytest.approx(total / 1000)


def test_slice_and_grain(client):
    full = client.get("/api/analytics").json()["summary"]
    sliced = client.get("/api/analytics?city=Lima&category=Moda&channel=Web&grain=quarter&dimension=category").json()
    assert 0 < sliced["summary"]["orders"] < full["orders"]
    assert [g["label"] for g in sliced["groups"]] == ["Moda"]
    assert len(sliced["trend"]) <= 8
    annual = client.get("/api/analytics?grain=year").json()
    assert len(annual["trend"]) == 2


@pytest.mark.parametrize("query", ["start=2025-01-01&end=2024-01-01", "start=bad", "dimension=order_id", "city=' OR 1=1--", "grain=week", "limit=999"])
def test_validation(client, query):
    assert client.get("/api/analytics?" + query).status_code == 422


def test_empty(client):
    data = client.get("/api/analytics?start=2030-01-01&end=2030-12-31").json()
    assert data["summary"]["orders"] == 0
    assert data["summary"]["margin"] == 0
    assert data["trend"] == []


def test_concurrent_reads(client):
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.get("/api/analytics?city=Lima").json(), range(8)))
    assert all(r == responses[0] for r in responses)


def test_known_fixture(tmp_path):
    path = tmp_path / "known.duckdb"
    build(path, count=1)
    with duckdb.connect(str(path)) as con:
        con.execute("DELETE FROM fact_sales")
        con.executemany("INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?,?)", [
            (1, date(2024, 1, 1), 1, 1, "Web", 2, Decimal("100.00"), Decimal("60.00")),
            (2, date(2024, 2, 1), 2, 2, "Tienda", 1, Decimal("50.00"), Decimal("40.00")),
        ])
    with TestClient(create_app(path)) as c:
        data = c.get("/api/analytics").json()
        assert data["summary"] == {"orders": 2, "units": 3, "revenue": 150.0,
                                   "profit": 50.0, "average_order": 75.0,
                                   "margin": pytest.approx(100 / 3)}
        assert data["trend"][1]["change"] == -50
        assert c.get("/api/analytics?city=Lima").json()["summary"]["revenue"] == 100


def test_generator_reproducible(tmp_path):
    checksums = []
    for name in ["a", "b"]:
        path = tmp_path / f"{name}.duckdb"
        build(path, count=25)
        with duckdb.connect(str(path), read_only=True) as con:
            checksums.append(con.execute("SELECT * FROM fact_sales ORDER BY order_id").fetchall())
    assert checksums[0] == checksums[1]
