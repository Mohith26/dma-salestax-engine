from taxgrid.engine import determine_invoice

from conftest import make_invoice


def line(category, unit, qty=1):
    return {"line_id": "1", "category": category,
            "unit_price_cents": unit, "quantity": qty}


def to_city(city, **kw):
    return make_invoice(ship_from="CI-CD-00-0" if not city.startswith("CI-CD") else "CI-MW-00-0",
                        ship_to=city, **kw)


def test_prescription_drugs_exempt_everywhere(ds):
    for city in ("CI-CD-00-0", "CI-MW-00-0", "CI-JN-00-0", "CI-HC-00-0"):
        res = determine_invoice(to_city(city, lines=[line("prescription_drugs", 9999)]), ds)
        assert res["tax_cents"] == 0


def test_groceries_exempt_in_CD_taxable_in_VD(ds):
    exempt = determine_invoice(to_city("CI-CD-00-0", lines=[line("groceries", 5000)]), ds)
    assert exempt["tax_cents"] == 0
    taxed = determine_invoice(to_city("CI-VD-00-0", lines=[line("groceries", 5000)]), ds)
    assert taxed["tax_cents"] > 0


def test_saas_split_by_state(ds):
    taxed = determine_invoice(to_city("CI-CD-00-0", lines=[line("saas", 100000)]), ds)
    assert taxed["tax_cents"] > 0
    exempt = determine_invoice(to_city("CI-TS-00-0", lines=[line("saas", 100000)]), ds)
    assert exempt["tax_cents"] == 0


def test_clothing_threshold_below_at_above(ds):
    below = determine_invoice(to_city("CI-MW-00-0", lines=[line("clothing", 10999)]), ds)
    at = determine_invoice(to_city("CI-MW-00-0", lines=[line("clothing", 11000)]), ds)
    above = determine_invoice(to_city("CI-MW-00-0", lines=[line("clothing", 11001)]), ds)
    assert below["tax_cents"] == 0
    assert at["tax_cents"] > 0
    assert above["tax_cents"] > 0


def test_threshold_is_per_unit_not_extended_amount(ds):
    # 3 units at 10999 extend to 32997, still exempt because per item price is under threshold
    res = determine_invoice(to_city("CI-MW-00-0", lines=[line("clothing", 10999, qty=3)]), ds)
    assert res["tax_cents"] == 0


def test_clothing_fully_exempt_in_JN(ds):
    res = determine_invoice(to_city("CI-JN-00-0", lines=[line("clothing", 999999)]), ds)
    assert res["tax_cents"] == 0


def test_exempt_line_has_reason_in_audit(ds):
    res = determine_invoice(to_city("CI-CD-00-0", lines=[line("groceries", 5000)]), ds)
    audit = res["lines"][0]["audit"]
    tax_steps = [a for a in audit if a["step"] == "taxability"]
    assert tax_steps[0]["result"] == "exempt"
    assert "grocery" in tax_steps[0]["reason"]
