"""Engine only throughput benchmark. Writes results/bench_engine.json.

Usage: python scripts/bench.py [n_lines] [seed]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from taxgrid.dataset import load
from taxgrid.engine import determine_invoice
from taxgrid.seeded import iter_invoices


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    ds = load()
    invoices = list(iter_invoices(ds, seed, n))

    # warmup
    for inv in invoices[:2000]:
        determine_invoice(inv, ds)

    t0 = time.perf_counter()
    tax = 0
    for inv in invoices:
        tax += determine_invoice(inv, ds)["tax_cents"]
    elapsed = time.perf_counter() - t0

    out = {
        "lines": n,
        "seed": seed,
        "elapsed_seconds": round(elapsed, 3),
        "lines_per_second": round(n / elapsed, 1),
        "total_tax_cents_checksum": tax,
        "note": "single thread, engine only, invoices pre generated in memory",
    }
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "results"), exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), "..", "results", "bench_engine.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
