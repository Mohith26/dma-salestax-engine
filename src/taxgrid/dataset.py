"""Load and index the committed jurisdiction dataset.

The dataset is entirely invented. Loading builds the lookup structures the
engine needs: city -> jurisdiction stack, effective-dated rate tables keyed
by date ordinal, the taxability matrix, and exemption certificates.
"""
import bisect
import json
import os
from datetime import date

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def parse_date(s: str) -> int:
    """ISO date string to ordinal for fast comparisons."""
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d)).toordinal()


class RateTable:
    """Effective-dated rates for one jurisdiction (time travel lookups)."""

    __slots__ = ("ordinals", "rates")

    def __init__(self, rows):
        rows = sorted(rows, key=lambda r: r["effective_from"])
        self.ordinals = [parse_date(r["effective_from"]) for r in rows]
        self.rates = [int(r["rate_bps"]) for r in rows]

    def rate_on(self, ordinal: int):
        """Rate in bps effective on the given date, or None before first row."""
        i = bisect.bisect_right(self.ordinals, ordinal) - 1
        if i < 0:
            return None
        return self.rates[i]


class Jurisdiction:
    __slots__ = ("id", "level", "name", "state", "parent", "sourcing",
                 "rounding", "table")

    def __init__(self, row):
        self.id = row["id"]
        self.level = row["level"]
        self.name = row["name"]
        self.state = row["state"]
        self.parent = row.get("parent")
        self.sourcing = row.get("sourcing")
        self.rounding = row["rounding"]
        self.table = RateTable(row["rates"])


class Dataset:
    def __init__(self, data_dir=DATA_DIR):
        with open(os.path.join(data_dir, "jurisdictions.json")) as f:
            jraw = json.load(f)["jurisdictions"]
        with open(os.path.join(data_dir, "taxability.json")) as f:
            traw = json.load(f)
        with open(os.path.join(data_dir, "certificates.json")) as f:
            craw = json.load(f)["certificates"]

        self.jurisdictions = {}
        districts_by_city = {}
        for row in jraw:
            j = Jurisdiction(row)
            self.jurisdictions[j.id] = j
            if j.level == "special":
                for city in row["covers_cities"]:
                    districts_by_city.setdefault(city, []).append(j.id)

        # city -> ordered stack of jurisdiction ids (state, county, city, specials)
        self.stack_by_city = {}
        for j in self.jurisdictions.values():
            if j.level != "city":
                continue
            county = self.jurisdictions[j.parent]
            state = self.jurisdictions[county.parent]
            stack = [state.id, county.id, j.id]
            stack.extend(sorted(districts_by_city.get(j.id, [])))
            self.stack_by_city[j.id] = stack

        self.categories = set(traw["categories"])
        self.matrix = traw["matrix"]

        self.certificates = {}
        for c in craw:
            self.certificates[c["id"]] = {
                "id": c["id"],
                "kind": c["kind"],
                "categories": set(c["categories"]),
                "valid_from": parse_date(c["valid_from"]),
                "valid_to": parse_date(c["valid_to"]),
            }

    def city(self, city_id: str) -> Jurisdiction:
        j = self.jurisdictions.get(city_id)
        if j is None or j.level != "city":
            raise KeyError(f"unknown city: {city_id}")
        return j

    def taxability(self, state_code: str, category: str) -> dict:
        if category not in self.categories:
            raise KeyError(f"unknown category: {category}")
        return self.matrix[state_code][category]


_default = None


def load() -> Dataset:
    """Shared default dataset instance."""
    global _default
    if _default is None:
        _default = Dataset()
    return _default
