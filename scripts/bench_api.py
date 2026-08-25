"""In process API latency benchmark using the ASGI test client.

Usage: python scripts/bench_api.py [n_requests]
Writes results/bench_api.json with p50/p95/p99 per request latency.
"""
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi.testclient import TestClient

from taxgrid.api import app
from taxgrid.dataset import load
from taxgrid.seeded import iter_invoices


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    ds = load()
    payloads = []
    for inv in iter_invoices(ds, 99, n):
        inv.pop("invoice_id")
        payloads.append(inv)

    client = TestClient(app)
    for p in payloads[:200]:
        assert client.post("/determine", json=p).status_code == 200

    lat = []
    t_all = time.perf_counter()
    for p in payloads:
        t0 = time.perf_counter()
        r = client.post("/determine", json=p)
        lat.append((time.perf_counter() - t0) * 1000.0)
        assert r.status_code == 200
    wall = time.perf_counter() - t_all

    lat.sort()
    out = {
        "requests": n,
        "p50_ms": round(statistics.median(lat), 3),
        "p95_ms": round(lat[int(0.95 * n) - 1], 3),
        "p99_ms": round(lat[int(0.99 * n) - 1], 3),
        "mean_ms": round(sum(lat) / n, 3),
        "requests_per_second": round(n / wall, 1),
        "note": "in process ASGI TestClient, single thread, includes JSON serialization",
    }
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "results"), exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), "..", "results", "bench_api.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
