"""Fast in-suite slice of the engine vs oracle comparison.

The full 1M line run lives in scripts/verify_oracle.py; this keeps a 25k line
slice in the regular suite so regressions show up on every test run.
"""
from taxgrid.engine import determine_invoice
from taxgrid.seeded import iter_invoices

from conftest import make_invoice


def test_engine_matches_oracle_on_25k_seeded_lines(ds, oracle):
    mismatches = 0
    for inv in iter_invoices(ds, 1234, 25000):
        res = determine_invoice(inv, ds)
        line = res["lines"][0]
        engine = (line["tax_cents"],
                  [(b["jurisdiction"], b["tax_cents"]) for b in line["breakdown"]])
        assert engine == oracle.line_tax(inv["lines"][0], inv)
        mismatches += 0
    assert mismatches == 0


def test_oracle_agrees_on_multi_line_invoice(ds, oracle):
    inv = make_invoice(lines=[
        {"line_id": "1", "category": "electronics", "unit_price_cents": 1250, "quantity": 3},
        {"line_id": "2", "category": "groceries", "unit_price_cents": 777, "quantity": 2},
        {"line_id": "3", "category": "saas", "unit_price_cents": 99999, "quantity": 1},
    ])
    res = determine_invoice(inv, ds)
    o_total, per_line = oracle.invoice_tax(inv)
    assert res["tax_cents"] == o_total
    for got, (want_total, want_parts) in zip(res["lines"], per_line):
        assert got["tax_cents"] == want_total
        assert [(b["jurisdiction"], b["tax_cents"]) for b in got["breakdown"]] == want_parts


def test_oracle_rejects_missing_rate_like_engine(oracle):
    inv = make_invoice(date="2019-06-01")
    try:
        oracle.line_tax(inv["lines"][0], inv)
        raised = False
    except ValueError:
        raised = True
    assert raised
