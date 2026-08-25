"""Seeded random invoice generator shared by the oracle run and benchmarks."""
import random

CATEGORIES = [
    "groceries", "prepared_food", "candy", "soda", "clothing", "footwear",
    "saas", "downloadable_software", "physical_software", "electronics",
    "furniture", "books", "digital_books", "medical_devices", "otc_drugs",
    "prescription_drugs", "cleaning_services", "consulting_services",
    "machinery", "raw_materials", "luxury_goods", "office_supplies",
]


def iter_invoices(ds, seed, n_lines):
    """Yield single line invoices until n_lines lines have been produced."""
    rng = random.Random(seed)
    cities = sorted(ds.stack_by_city.keys())
    certs = sorted(ds.certificates.keys())
    for i in range(n_lines):
        y = rng.choice([2022, 2023, 2024, 2025, 2026])
        m = rng.randrange(1, 13)
        d = rng.randrange(1, 29)
        invoice = {
            "invoice_id": f"SEED-{i}",
            "date": f"{y:04d}-{m:02d}-{d:02d}",
            "ship_from": rng.choice(cities),
            "ship_to": rng.choice(cities),
            "transaction_type": "use" if rng.random() < 0.05 else "sale",
            "exemption_certificate": rng.choice(certs) if rng.random() < 0.03 else None,
            "lines": [{
                "line_id": "1",
                "category": rng.choice(CATEGORIES),
                "unit_price_cents": rng.randrange(1, 50001),
                "quantity": rng.randrange(1, 6),
            }],
        }
        yield invoice
