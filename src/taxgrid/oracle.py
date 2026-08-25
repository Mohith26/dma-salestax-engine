"""Independent oracle that recomputes every determination from scratch.

This intentionally shares no code with the engine. It parses the raw JSON
files itself, compares ISO date strings lexicographically instead of using
ordinals, and does the money math with decimal.Decimal quantization instead
of integer quotient/remainder arithmetic. If both implementations agree on
millions of randomized lines, a shared systematic bug is much less likely.
"""
import json
import os
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN, ROUND_HALF_EVEN

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

_DEC_MODES = {
    "half_up": ROUND_HALF_UP,
    "half_down": ROUND_HALF_DOWN,
    "half_even": ROUND_HALF_EVEN,
}


class Oracle:
    def __init__(self, data_dir=DATA_DIR):
        with open(os.path.join(data_dir, "jurisdictions.json")) as f:
            rows = json.load(f)["jurisdictions"]
        with open(os.path.join(data_dir, "taxability.json")) as f:
            t = json.load(f)
        with open(os.path.join(data_dir, "certificates.json")) as f:
            certs = json.load(f)["certificates"]

        self.j = {r["id"]: r for r in rows}
        self.matrix = t["matrix"]
        self.certs = {c["id"]: c for c in certs}
        self.specials_by_city = {}
        for r in rows:
            if r["level"] == "special":
                for c in r["covers_cities"]:
                    self.specials_by_city.setdefault(c, []).append(r["id"])

    def _rate_on(self, jur_id, iso_date):
        best = None
        for row in self.j[jur_id]["rates"]:
            if row["effective_from"] <= iso_date:
                if best is None or row["effective_from"] > best["effective_from"]:
                    best = row
        return None if best is None else best["rate_bps"]

    def _stack(self, city_id):
        city = self.j[city_id]
        county = self.j[city["parent"]]
        state = self.j[county["parent"]]
        return [state["id"], county["id"], city["id"]] + \
            sorted(self.specials_by_city.get(city_id, []))

    def _situs(self, invoice):
        to = self.j[invoice["ship_to"]]
        frm = self.j[invoice["ship_from"]]
        if invoice.get("transaction_type", "sale") == "use":
            return invoice["ship_to"]
        state = self.j["ST-" + to["state"]]
        if frm["state"] == to["state"] and state["sourcing"] == "origin":
            return invoice["ship_from"]
        return invoice["ship_to"]

    def _cert_exempts(self, invoice, category):
        cid = invoice.get("exemption_certificate")
        if not cid:
            return False
        c = self.certs[cid]
        d = invoice["date"]
        if not (c["valid_from"] <= d <= c["valid_to"]):
            return False
        return "*" in c["categories"] or category in c["categories"]

    def line_tax(self, line, invoice):
        """Returns (tax_cents_total, [(jurisdiction_id, tax_cents), ...])."""
        situs_city = self._situs(invoice)
        state_code = self.j[situs_city]["state"]
        rule = self.matrix[state_code][line["category"]]
        unit = int(line["unit_price_cents"])
        if rule["kind"] == "exempt":
            return 0, []
        if rule["kind"] == "threshold" and unit < rule["threshold_cents"]:
            return 0, []
        if self._cert_exempts(invoice, line["category"]):
            return 0, []
        gross = Decimal(unit * int(line["quantity"]))
        parts = []
        total = 0
        for jid in self._stack(situs_city):
            bps = self._rate_on(jid, invoice["date"])
            if bps is None:
                raise ValueError(f"no rate for {jid} on {invoice['date']}")
            exact = gross * Decimal(bps) / Decimal(10000)
            cents = int(exact.quantize(Decimal("1"),
                                       rounding=_DEC_MODES[self.j[jid]["rounding"]]))
            parts.append((jid, cents))
            total += cents
        return total, parts

    def invoice_tax(self, invoice):
        total = 0
        per_line = []
        for line in invoice["lines"]:
            t, parts = self.line_tax(line, invoice)
            total += t
            per_line.append((t, parts))
        return total, per_line
