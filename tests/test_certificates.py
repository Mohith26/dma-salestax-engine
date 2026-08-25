from taxgrid.engine import determine_invoice

from conftest import make_invoice


def test_nonprofit_cert_exempts_everything(ds):
    res = determine_invoice(make_invoice(exemption_certificate="CERT-001"), ds)
    assert res["tax_cents"] == 0
    assert res["lines"][0]["taxable"] is False


def test_resale_cert_only_covers_listed_categories(ds):
    covered = determine_invoice(make_invoice(
        exemption_certificate="CERT-000",
        lines=[{"line_id": "1", "category": "electronics",
                "unit_price_cents": 10000, "quantity": 1}]), ds)
    assert covered["tax_cents"] == 0
    not_covered = determine_invoice(make_invoice(
        exemption_certificate="CERT-000",
        lines=[{"line_id": "1", "category": "prepared_food",
                "unit_price_cents": 10000, "quantity": 1}]), ds)
    assert not_covered["tax_cents"] > 0


def test_expired_cert_does_not_apply(ds):
    res = determine_invoice(make_invoice(
        date="2025-03-01", exemption_certificate="CERT-000"), ds)
    assert res["tax_cents"] > 0
    notes = [a for a in res["lines"][0]["audit"] if a["step"] == "certificate"]
    assert notes and notes[0]["applied"] is False
    assert "not valid" in notes[0]["reason"]


def test_cert_not_yet_valid_does_not_apply(ds):
    # CERT-008 starts 2024-06-01
    res = determine_invoice(make_invoice(
        date="2024-01-15", exemption_certificate="CERT-008"), ds)
    assert res["tax_cents"] > 0


def test_cert_application_recorded_in_audit(ds):
    res = determine_invoice(make_invoice(exemption_certificate="CERT-001"), ds)
    notes = [a for a in res["lines"][0]["audit"] if a["step"] == "certificate"]
    assert notes and notes[0]["applied"] is True
    assert "CERT-001" in notes[0]["reason"]


def test_cert_irrelevant_on_already_exempt_line(ds):
    res = determine_invoice(make_invoice(
        ship_from="CI-MW-00-0", ship_to="CI-CD-00-0",
        exemption_certificate="CERT-001",
        lines=[{"line_id": "1", "category": "groceries",
                "unit_price_cents": 5000, "quantity": 1}]), ds)
    steps = [a["step"] for a in res["lines"][0]["audit"]]
    assert "certificate" not in steps
    assert res["tax_cents"] == 0
