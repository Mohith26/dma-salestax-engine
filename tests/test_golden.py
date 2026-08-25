import json
import os

import pytest

from taxgrid.engine import determine_invoice

GOLDEN = os.path.join(os.path.dirname(__file__), "..", "golden", "golden_invoices.json")

with open(GOLDEN) as f:
    CASES = json.load(f)["cases"]


def test_at_least_ten_golden_cases():
    assert len(CASES) >= 10


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_golden_invoice(ds, case):
    res = determine_invoice(case["invoice"], ds)
    exp = case["expected"]
    assert res["tax_cents"] == exp["tax_cents"]
    assert res["gross_cents"] == exp["gross_cents"]
    assert res["total_cents"] == exp["total_cents"]
    if "accrual" in exp:
        assert res["accrual"] == exp["accrual"]
    assert len(res["lines"]) == len(exp["lines"])
    for got, want in zip(res["lines"], exp["lines"]):
        assert got["tax_cents"] == want["tax_cents"]
        assert got["taxable"] == want["taxable"]
        assert [b["tax_cents"] for b in got["breakdown"]] == want["breakdown_cents"]
