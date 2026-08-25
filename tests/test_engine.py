import pytest

from taxgrid.engine import DeterminationError, determine_invoice

from conftest import make_invoice


def test_breakdown_sums_to_line_tax(ds):
    res = determine_invoice(make_invoice(), ds)
    line = res["lines"][0]
    assert sum(b["tax_cents"] for b in line["breakdown"]) == line["tax_cents"]


def test_invoice_totals_sum_lines(ds):
    inv = make_invoice(lines=[
        {"line_id": "1", "category": "electronics", "unit_price_cents": 10000, "quantity": 1},
        {"line_id": "2", "category": "furniture", "unit_price_cents": 333, "quantity": 3},
    ])
    res = determine_invoice(inv, ds)
    assert res["gross_cents"] == sum(l["gross_cents"] for l in res["lines"])
    assert res["tax_cents"] == sum(l["tax_cents"] for l in res["lines"])
    assert res["total_cents"] == res["gross_cents"] + res["tax_cents"]


def test_quantity_multiplies_base(ds):
    one = determine_invoice(make_invoice(), ds)
    five = determine_invoice(make_invoice(lines=[
        {"line_id": "1", "category": "electronics", "unit_price_cents": 10000, "quantity": 5}]), ds)
    assert five["gross_cents"] == 5 * one["gross_cents"]
    # 10000 cents at these rates divides exactly, so tax scales exactly too
    assert five["tax_cents"] == 5 * one["tax_cents"]


def test_audit_trail_has_situs_taxability_and_rates(ds):
    res = determine_invoice(make_invoice(), ds)
    steps = [a["step"] for a in res["lines"][0]["audit"]]
    assert steps[0] == "situs"
    assert "taxability" in steps
    assert steps.count("rate") == len(res["lines"][0]["breakdown"])


def test_audit_rate_entries_are_integer_cents(ds):
    res = determine_invoice(make_invoice(), ds)
    for a in res["lines"][0]["audit"]:
        if a["step"] == "rate":
            assert isinstance(a["tax_cents"], int)
            assert isinstance(a["base_cents"], int)
            assert isinstance(a["rate_bps"], int)


def test_empty_invoice_rejected(ds):
    with pytest.raises(DeterminationError):
        determine_invoice(make_invoice(lines=[]), ds)


def test_bad_quantity_rejected(ds):
    with pytest.raises(DeterminationError):
        determine_invoice(make_invoice(lines=[
            {"line_id": "1", "category": "electronics", "unit_price_cents": 100, "quantity": 0}]), ds)


def test_bad_transaction_type_rejected(ds):
    with pytest.raises(DeterminationError):
        determine_invoice(make_invoice(transaction_type="refund"), ds)


def test_unknown_certificate_rejected(ds):
    with pytest.raises(DeterminationError):
        determine_invoice(make_invoice(exemption_certificate="CERT-999"), ds)


def test_date_before_rates_exist_rejected(ds):
    with pytest.raises(DeterminationError):
        determine_invoice(make_invoice(date="2019-06-01"), ds)


def test_zero_price_line_yields_zero_tax(ds):
    res = determine_invoice(make_invoice(lines=[
        {"line_id": "1", "category": "electronics", "unit_price_cents": 0, "quantity": 1}]), ds)
    assert res["tax_cents"] == 0


def test_default_dataset_used_when_none_passed():
    res = determine_invoice(make_invoice())
    assert res["tax_cents"] == 843
