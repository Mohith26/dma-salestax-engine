import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from taxgrid.dataset import load  # noqa: E402
from taxgrid.oracle import Oracle  # noqa: E402


@pytest.fixture(scope="session")
def ds():
    return load()


@pytest.fixture(scope="session")
def oracle():
    return Oracle()


def make_invoice(**kw):
    inv = {
        "invoice_id": "T-1",
        "date": "2023-01-15",
        "ship_from": "CI-CD-00-0",
        "ship_to": "CI-CD-00-1",
        "transaction_type": "sale",
        "lines": [{"line_id": "1", "category": "electronics",
                   "unit_price_cents": 10000, "quantity": 1}],
    }
    inv.update(kw)
    return inv
