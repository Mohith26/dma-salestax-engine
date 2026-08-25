"""Exhaustive rounding and threshold boundary matrix.

For every rounding mode we sweep bases that land the exact-half, just-below
and just-above remainder cases, checking the integer engine against a Decimal
reference. Then thresholds are probed one cent either side for every
threshold rule in the committed matrix.
"""
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN, ROUND_HALF_EVEN

import pytest

from taxgrid.engine import determine_invoice
from taxgrid.rounding import line_tax_cents

from conftest import make_invoice

DEC = {"half_up": ROUND_HALF_UP, "half_down": ROUND_HALF_DOWN,
       "half_even": ROUND_HALF_EVEN}


@pytest.mark.parametrize("mode", ["half_up", "half_down", "half_even"])
def test_mode_matches_decimal_reference_over_sweep(mode):
    # bases 1..4000 cents at rates chosen to generate many .5 ties (50, 150, 250 bps)
    # plus prime-ish rates for irregular remainders
    for rate in (50, 150, 250, 33, 41, 97, 693, 521):
        for base in range(1, 4001):
            got = line_tax_cents(base, rate, mode)
            want = int((Decimal(base) * Decimal(rate) / Decimal(10000))
                       .quantize(Decimal("1"), rounding=DEC[mode]))
            assert got == want, (base, rate, mode)


@pytest.mark.parametrize("mode", ["half_up", "half_down", "half_even"])
def test_every_exact_half_tie_up_to_1000(mode):
    # rate 50 bps makes base*50/10000 = base/200, so every odd multiple of 100 is a tie
    for base in range(100, 100001, 200):
        q = base // 200
        got = line_tax_cents(base, 50, mode)
        if mode == "half_up":
            assert got == q + 1
        elif mode == "half_down":
            assert got == q
        else:
            assert got == (q if q % 2 == 0 else q + 1)


def _threshold_rules(ds):
    out = []
    for state, row in ds.matrix.items():
        for cat, rule in row.items():
            if rule["kind"] == "threshold":
                out.append((state, cat, rule["threshold_cents"]))
    return out


def test_threshold_rules_exist_in_dataset(ds):
    rules = _threshold_rules(ds)
    assert len(rules) >= 3


def test_every_threshold_boundary_one_cent_each_side(ds):
    for state, cat, threshold in _threshold_rules(ds):
        city = f"CI-{state}-00-0"
        inv = make_invoice(ship_from="CI-CD-00-1" if state != "CD" else "CI-MW-00-0",
                           ship_to=city)
        for price, expect_taxable in ((threshold - 1, False),
                                      (threshold, True),
                                      (threshold + 1, True)):
            inv["lines"] = [{"line_id": "1", "category": cat,
                             "unit_price_cents": price, "quantity": 1}]
            res = determine_invoice(inv, ds)
            assert res["lines"][0]["taxable"] is expect_taxable, (state, cat, price)
            if not expect_taxable:
                assert res["tax_cents"] == 0
            else:
                assert res["tax_cents"] > 0
