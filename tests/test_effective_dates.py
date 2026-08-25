from taxgrid.dataset import parse_date
from taxgrid.engine import determine_invoice

from conftest import make_invoice


def test_same_invoice_both_sides_of_rate_change(ds):
    # SP-CD-00 goes from 22 to 97 bps effective 2024-04-01
    before = determine_invoice(make_invoice(date="2024-03-31"), ds)
    after = determine_invoice(make_invoice(date="2024-04-01"), ds)
    assert before["tax_cents"] == 843
    assert after["tax_cents"] == 918
    sp_before = [b for b in before["lines"][0]["breakdown"] if b["jurisdiction"] == "SP-CD-00"][0]
    sp_after = [b for b in after["lines"][0]["breakdown"] if b["jurisdiction"] == "SP-CD-00"][0]
    assert sp_before["rate_bps"] == 22
    assert sp_after["rate_bps"] == 97


def test_change_effective_on_exact_boundary_day(ds):
    j = ds.jurisdictions["SP-CD-00"]
    assert j.table.rate_on(parse_date("2024-03-31")) == 22
    assert j.table.rate_on(parse_date("2024-04-01")) == 97
    assert j.table.rate_on(parse_date("2024-12-31")) == 97
    assert j.table.rate_on(parse_date("2025-01-01")) == 47


def test_rate_decrease_honored(ds):
    # ST-HC dropped from 487 to 437 on 2024-01-01 and back to 487 on 2025-01-01
    j = ds.jurisdictions["ST-HC"]
    assert j.table.rate_on(parse_date("2023-12-31")) == 487
    assert j.table.rate_on(parse_date("2024-06-15")) == 437
    assert j.table.rate_on(parse_date("2025-06-15")) == 487


def test_every_jurisdiction_resolves_on_recent_date(ds):
    d = parse_date("2026-01-15")
    for j in ds.jurisdictions.values():
        assert j.table.rate_on(d) is not None


def test_all_layers_time_travel_together(ds):
    inv = make_invoice(ship_from="CI-MW-00-1", ship_to="CI-MW-00-0")
    early = determine_invoice(dict(inv, date="2023-01-15"), ds)
    late = determine_invoice(dict(inv, date="2025-08-15"), ds)
    rates_early = {b["jurisdiction"]: b["rate_bps"] for b in early["lines"][0]["breakdown"]}
    rates_late = {b["jurisdiction"]: b["rate_bps"] for b in late["lines"][0]["breakdown"]}
    # ST-MW 693 to 743, CO-MW-00 62 to 137, CI-MW-00-0 33 to 208
    assert rates_early["ST-MW"] == 693 and rates_late["ST-MW"] == 743
    assert rates_early["CO-MW-00"] == 62 and rates_late["CO-MW-00"] == 137
    assert rates_early["CI-MW-00-0"] == 33 and rates_late["CI-MW-00-0"] == 208
