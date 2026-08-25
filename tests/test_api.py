from fastapi.testclient import TestClient

from taxgrid.api import app

from conftest import make_invoice

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["jurisdictions"] >= 200


def test_determine_basic_invoice():
    r = client.post("/determine", json=make_invoice())
    assert r.status_code == 200
    body = r.json()
    assert body["tax_cents"] == 843
    assert body["total_cents"] == 10843
    assert body["lines"][0]["audit"]


def test_determine_use_tax():
    r = client.post("/determine", json=make_invoice(transaction_type="use",
                                                    ship_to="CI-MW-00-0"))
    assert r.status_code == 200
    assert r.json()["accrual"] is True


def test_unknown_city_is_422():
    r = client.post("/determine", json=make_invoice(ship_to="CI-XX-00-0"))
    assert r.status_code == 422


def test_bad_transaction_type_is_422():
    r = client.post("/determine", json=make_invoice(transaction_type="refund"))
    assert r.status_code == 422


def test_negative_price_rejected_by_schema():
    r = client.post("/determine", json=make_invoice(lines=[
        {"line_id": "1", "category": "electronics",
         "unit_price_cents": -5, "quantity": 1}]))
    assert r.status_code == 422


def test_missing_lines_rejected():
    inv = make_invoice()
    del inv["lines"]
    r = client.post("/determine", json=inv)
    assert r.status_code == 422
