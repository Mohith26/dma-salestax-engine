"""Generate the invented TaxGrid jurisdiction dataset.

Everything here is fictional. State names, codes, rates, taxability rules and
certificates are invented for testing a determination engine. None of it maps
to any real tax authority.

Deterministic: fixed seed, stable ordering, so the committed JSON is stable.
"""
import json
import os
import random

SEED = 20260817
OUT = os.path.join(os.path.dirname(__file__), "..", "data")

STATES = [
    ("CD", "Caldera"), ("MW", "Marlowe"), ("TS", "Tessara"), ("VD", "Verdant"),
    ("OS", "Ostara"), ("QL", "Quillon"), ("BK", "Brackenridge"), ("EW", "Ellsworth"),
    ("FW", "Fenwick"), ("GL", "Galena"), ("HC", "Halcyon"), ("IV", "Ironvale"),
    ("JN", "Juniper"), ("KE", "Kestrel"), ("LK", "Larkspur"),
]

# origin-sourced states (intrastate sales use ship_from situs), rest destination
ORIGIN_STATES = {"CD", "OS", "BK", "GL", "KE"}

COUNTY_NAMES = ["Ashford", "Briar", "Cinder", "Dunmore"]
CITY_NAMES = ["Northgate", "Eastwick", "Milton", "Harrow", "Selby", "Wrenfield",
              "Oakhurst", "Percival"]

CATEGORIES = [
    "groceries", "prepared_food", "candy", "soda", "clothing", "footwear",
    "saas", "downloadable_software", "physical_software", "electronics",
    "furniture", "books", "digital_books", "medical_devices", "otc_drugs",
    "prescription_drugs", "cleaning_services", "consulting_services",
    "machinery", "raw_materials", "luxury_goods", "office_supplies",
]

ROUND_MODES = ["half_up", "half_up", "half_up", "half_even", "half_down"]

CHANGE_DATES = ["2023-04-01", "2023-07-01", "2023-10-01", "2024-01-01",
                "2024-04-01", "2024-07-01", "2025-01-01", "2025-07-01"]


def make_rates(rng, base_lo, base_hi, allow_zero=False):
    """1 to 3 effective-dated rate rows in basis points."""
    if allow_zero and rng.random() < 0.15:
        first = 0
    else:
        first = rng.randrange(base_lo, base_hi + 1)
    rows = [{"effective_from": "2020-01-01", "rate_bps": first}]
    n_changes = rng.choice([0, 0, 1, 1, 1, 2])
    dates = sorted(rng.sample(CHANGE_DATES, n_changes))
    rate = first
    for d in dates:
        delta = rng.choice([-50, -25, 25, 25, 50, 50, 75, 100])
        rate = max(0, rate + delta)
        rows.append({"effective_from": d, "rate_bps": rate})
    return rows


def main():
    rng = random.Random(SEED)
    jurisdictions = []
    cities = []

    for code, name in STATES:
        jurisdictions.append({
            "id": f"ST-{code}",
            "level": "state",
            "name": name,
            "state": code,
            "parent": None,
            "sourcing": "origin" if code in ORIGIN_STATES else "destination",
            "rounding": rng.choice(ROUND_MODES),
            "rates": make_rates(rng, 400, 725),
        })
        for ci, cname in enumerate(COUNTY_NAMES):
            county_id = f"CO-{code}-{ci:02d}"
            jurisdictions.append({
                "id": county_id,
                "level": "county",
                "name": f"{cname} County",
                "state": code,
                "parent": f"ST-{code}",
                "rounding": rng.choice(ROUND_MODES),
                "rates": make_rates(rng, 25, 200, allow_zero=True),
            })
            picked = rng.sample(CITY_NAMES, 2)
            for cy, cyname in enumerate(picked):
                city_id = f"CI-{code}-{ci:02d}-{cy}"
                jurisdictions.append({
                    "id": city_id,
                    "level": "city",
                    "name": cyname,
                    "state": code,
                    "parent": county_id,
                    "rounding": rng.choice(ROUND_MODES),
                    "rates": make_rates(rng, 0, 250, allow_zero=True),
                })
                cities.append(city_id)

    # 30 special districts, each covers 1 to 3 cities in a single state
    by_state = {}
    for c in cities:
        by_state.setdefault(c.split("-")[1], []).append(c)
    kinds = ["Transit Authority", "Stadium District", "Fire District",
             "Library District", "Crime Control District"]
    for i in range(30):
        code = STATES[i % len(STATES)][0]
        pool = by_state[code]
        covered = sorted(rng.sample(pool, rng.choice([1, 2, 2, 3])))
        jurisdictions.append({
            "id": f"SP-{code}-{i:02d}",
            "level": "special",
            "name": f"{STATES[i % len(STATES)][1]} {rng.choice(kinds)} {i}",
            "state": code,
            "parent": f"ST-{code}",
            "covers_cities": covered,
            "rounding": rng.choice(ROUND_MODES),
            "rates": make_rates(rng, 10, 100),
        })

    # taxability matrix: state x category
    matrix = {}
    grocery_exempt = {"CD", "MW", "TS", "OS", "BK", "FW", "HC", "JN", "LK"}
    saas_taxable = {"CD", "VD", "QL", "EW", "GL", "IV", "KE", "MW"}
    consulting_taxable = {"OS", "BK", "TS", "LK"}
    machinery_exempt = {"CD", "TS", "EW", "GL", "JN", "KE"}
    digital_books_exempt = {"MW", "OS", "HC", "FW"}
    otc_exempt = {"VD", "QL", "BK", "IV", "LK", "CD"}
    raw_materials_exempt = {"CD", "MW", "TS", "VD", "OS", "QL", "BK", "EW"}
    for code, _ in STATES:
        row = {}
        for cat in CATEGORIES:
            rule = {"kind": "taxable"}
            if cat == "prescription_drugs":
                rule = {"kind": "exempt", "reason": "prescription drug exemption"}
            elif cat == "groceries" and code in grocery_exempt:
                rule = {"kind": "exempt", "reason": "grocery exemption"}
            elif cat == "medical_devices":
                rule = {"kind": "exempt", "reason": "medical device exemption"}
            elif cat == "otc_drugs" and code in otc_exempt:
                rule = {"kind": "exempt", "reason": "over the counter drug exemption"}
            elif cat == "saas" and code not in saas_taxable:
                rule = {"kind": "exempt", "reason": "electronically delivered software not enumerated as taxable"}
            elif cat == "digital_books" and code in digital_books_exempt:
                rule = {"kind": "exempt", "reason": "digital goods exemption"}
            elif cat == "consulting_services" and code not in consulting_taxable:
                rule = {"kind": "exempt", "reason": "professional services not enumerated"}
            elif cat == "machinery" and code in machinery_exempt:
                rule = {"kind": "exempt", "reason": "manufacturing machinery exemption"}
            elif cat == "raw_materials" and code in raw_materials_exempt:
                rule = {"kind": "exempt", "reason": "resale component exemption"}
            elif cat == "clothing" and code == "MW":
                rule = {"kind": "threshold", "threshold_cents": 11000,
                        "note": "per item clothing exemption under 110.00"}
            elif cat == "clothing" and code == "HC":
                rule = {"kind": "threshold", "threshold_cents": 17500,
                        "note": "per item clothing exemption under 175.00"}
            elif cat == "clothing" and code == "JN":
                rule = {"kind": "exempt", "reason": "clothing fully exempt"}
            elif cat == "footwear" and code == "MW":
                rule = {"kind": "threshold", "threshold_cents": 11000,
                        "note": "per item footwear exemption under 110.00"}
            row[cat] = rule
        matrix[code] = row

    certificates = []
    cert_kinds = [("resale", ["electronics", "furniture", "raw_materials",
                              "physical_software", "office_supplies"]),
                  ("nonprofit", ["*"]), ("government", ["*"]),
                  ("manufacturing", ["machinery", "raw_materials"])]
    for i in range(12):
        kind, cats = cert_kinds[i % 4]
        certificates.append({
            "id": f"CERT-{i:03d}",
            "kind": kind,
            "categories": cats,
            "valid_from": "2021-01-01" if i < 8 else "2024-06-01",
            "valid_to": "2026-12-31" if i % 3 else "2024-12-31",
        })

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "jurisdictions.json"), "w") as f:
        json.dump({"seed": SEED, "jurisdictions": jurisdictions}, f, indent=1, sort_keys=True)
    with open(os.path.join(OUT, "taxability.json"), "w") as f:
        json.dump({"categories": CATEGORIES, "matrix": matrix}, f, indent=1, sort_keys=True)
    with open(os.path.join(OUT, "certificates.json"), "w") as f:
        json.dump({"certificates": certificates}, f, indent=1, sort_keys=True)

    counts = {}
    for j in jurisdictions:
        counts[j["level"]] = counts.get(j["level"], 0) + 1
    print("jurisdictions:", len(jurisdictions), counts)
    print("cities:", len(cities), "categories:", len(CATEGORIES))


if __name__ == "__main__":
    main()
