"""Line level sales and use tax determination.

Pipeline per line: situs resolution -> taxability -> exemption certificate ->
rate stack (effective dated) -> per jurisdiction penny rounding -> audit trail.

Documented sourcing model:
  * Sale, ship_from and ship_to in the same state, state is origin sourced:
    situs is the ship_from city.
  * Any other sale (destination state, or interstate): situs is ship_to.
  * Use tax accrual (transaction_type "use"): situs is always ship_to and the
    computed amount is an accrual the buyer self assesses, not collected tax.

Documented taxability model: the state level matrix decides taxability for the
whole stack. Local only taxability overrides are out of scope.

All money is integer cents; rates are integer basis points.
"""
from .dataset import Dataset, load, parse_date
from .rounding import line_tax_cents


class DeterminationError(ValueError):
    pass


def _resolve_situs(ds: Dataset, ship_from: str, ship_to: str, txn_type: str):
    to_city = ds.city(ship_to)
    from_city = ds.city(ship_from)
    if txn_type == "use":
        return to_city, "use tax accrues at destination"
    to_state = ds.jurisdictions[f"ST-{to_city.state}"]
    if from_city.state == to_city.state and to_state.sourcing == "origin":
        return from_city, f"intrastate sale in origin sourced state {to_city.state}"
    if from_city.state == to_city.state:
        return to_city, f"intrastate sale in destination sourced state {to_city.state}"
    return to_city, "interstate sale sources to destination"


def _certificate_status(ds: Dataset, cert_id, category: str, ordinal: int):
    """Returns (applies, note)."""
    if not cert_id:
        return False, None
    cert = ds.certificates.get(cert_id)
    if cert is None:
        raise DeterminationError(f"unknown exemption certificate: {cert_id}")
    if not (cert["valid_from"] <= ordinal <= cert["valid_to"]):
        return False, f"certificate {cert_id} not valid on invoice date"
    if "*" in cert["categories"] or category in cert["categories"]:
        return True, f"certificate {cert_id} ({cert['kind']}) covers {category}"
    return False, f"certificate {cert_id} does not cover {category}"


def determine_line(ds: Dataset, line: dict, invoice: dict) -> dict:
    category = line["category"]
    qty = int(line["quantity"])
    unit = int(line["unit_price_cents"])
    if qty <= 0 or unit < 0:
        raise DeterminationError("quantity must be positive and unit price non negative")
    txn_type = invoice.get("transaction_type", "sale")
    if txn_type not in ("sale", "use"):
        raise DeterminationError(f"unknown transaction_type: {txn_type}")
    ordinal = parse_date(invoice["date"])
    gross = unit * qty

    situs_city, situs_reason = _resolve_situs(
        ds, invoice["ship_from"], invoice["ship_to"], txn_type)
    audit = [{"step": "situs", "city": situs_city.id,
              "state": situs_city.state, "reason": situs_reason}]

    rule = ds.taxability(situs_city.state, category)
    taxable = True
    if rule["kind"] == "exempt":
        taxable = False
        audit.append({"step": "taxability", "result": "exempt",
                      "reason": rule["reason"]})
    elif rule["kind"] == "threshold":
        if unit < rule["threshold_cents"]:
            taxable = False
            audit.append({"step": "taxability", "result": "exempt",
                          "reason": f"unit price below threshold {rule['threshold_cents']} cents"})
        else:
            audit.append({"step": "taxability", "result": "taxable",
                          "reason": f"unit price at or above threshold {rule['threshold_cents']} cents"})
    else:
        audit.append({"step": "taxability", "result": "taxable",
                      "reason": "category taxable in situs state"})

    if taxable:
        applies, note = _certificate_status(
            ds, invoice.get("exemption_certificate"), category, ordinal)
        if note:
            audit.append({"step": "certificate", "applied": applies, "reason": note})
        if applies:
            taxable = False

    breakdown = []
    total = 0
    if taxable:
        for jid in ds.stack_by_city[situs_city.id]:
            jur = ds.jurisdictions[jid]
            rate = jur.table.rate_on(ordinal)
            if rate is None:
                raise DeterminationError(
                    f"no rate effective for {jid} on {invoice['date']}")
            tax = line_tax_cents(gross, rate, jur.rounding)
            total += tax
            entry = {"jurisdiction": jid, "level": jur.level, "rate_bps": rate,
                     "base_cents": gross, "rounding": jur.rounding,
                     "tax_cents": tax}
            breakdown.append(entry)
            audit.append(dict(entry, step="rate"))

    return {
        "line_id": line.get("line_id"),
        "category": category,
        "gross_cents": gross,
        "taxable": taxable,
        "situs_city": situs_city.id,
        "tax_cents": total,
        "accrual": txn_type == "use",
        "breakdown": breakdown,
        "audit": audit,
    }


def determine_invoice(invoice: dict, ds: Dataset = None) -> dict:
    ds = ds or load()
    if not invoice.get("lines"):
        raise DeterminationError("invoice has no lines")
    lines = [determine_line(ds, ln, invoice) for ln in invoice["lines"]]
    gross = sum(l["gross_cents"] for l in lines)
    tax = sum(l["tax_cents"] for l in lines)
    return {
        "invoice_id": invoice.get("invoice_id"),
        "date": invoice["date"],
        "transaction_type": invoice.get("transaction_type", "sale"),
        "gross_cents": gross,
        "tax_cents": tax,
        "total_cents": gross + tax,
        "accrual": invoice.get("transaction_type", "sale") == "use",
        "lines": lines,
    }
