from taxgrid.engine import determine_invoice

from conftest import make_invoice


def test_origin_state_intrastate_uses_ship_from(ds):
    res = determine_invoice(make_invoice(ship_from="CI-CD-00-0", ship_to="CI-CD-00-1"), ds)
    assert res["lines"][0]["situs_city"] == "CI-CD-00-0"


def test_destination_state_intrastate_uses_ship_to(ds):
    res = determine_invoice(make_invoice(ship_from="CI-MW-00-1", ship_to="CI-MW-00-0"), ds)
    assert res["lines"][0]["situs_city"] == "CI-MW-00-0"


def test_interstate_always_destination(ds):
    # ship_from is in origin sourced CD, but interstate goes to destination
    res = determine_invoice(make_invoice(ship_from="CI-CD-00-0", ship_to="CI-MW-00-0"), ds)
    assert res["lines"][0]["situs_city"] == "CI-MW-00-0"


def test_use_tax_ignores_origin_sourcing(ds):
    res = determine_invoice(make_invoice(
        ship_from="CI-CD-00-1", ship_to="CI-CD-00-0", transaction_type="use"), ds)
    assert res["lines"][0]["situs_city"] == "CI-CD-00-0"
    assert res["accrual"] is True
    assert res["lines"][0]["accrual"] is True


def test_sale_is_not_accrual(ds):
    res = determine_invoice(make_invoice(), ds)
    assert res["accrual"] is False


def test_special_districts_included_in_stack(ds):
    res = determine_invoice(make_invoice(), ds)
    levels = [b["level"] for b in res["lines"][0]["breakdown"]]
    assert levels[:3] == ["state", "county", "city"]
    assert "special" in levels
