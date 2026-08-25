"""Run the engine and the independent oracle over seeded invoice lines and
count mismatches. Writes results/oracle_verify.json.

Usage: python scripts/verify_oracle.py [n_lines] [seed]
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from taxgrid.dataset import load
from taxgrid.engine import determine_invoice
from taxgrid.oracle import Oracle
from taxgrid.seeded import iter_invoices


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    ds = load()
    oracle = Oracle()

    mismatches = 0
    examples = []
    t0 = time.perf_counter()
    for inv in iter_invoices(ds, seed, n):
        res = determine_invoice(inv, ds)
        line = res["lines"][0]
        engine_pair = (line["tax_cents"],
                       [(b["jurisdiction"], b["tax_cents"]) for b in line["breakdown"]])
        o_total, o_parts = oracle.line_tax(inv["lines"][0], inv)
        if engine_pair != (o_total, o_parts):
            mismatches += 1
            if len(examples) < 10:
                examples.append({"invoice": inv, "engine": engine_pair,
                                 "oracle": [o_total, o_parts]})
    elapsed = time.perf_counter() - t0

    out = {
        "lines": n,
        "seed": seed,
        "mismatches": mismatches,
        "elapsed_seconds": round(elapsed, 2),
        "pair_lines_per_second": round(n / elapsed, 1),
        "note": "both engine and oracle ran on every line; single thread",
        "mismatch_examples": examples,
    }
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "results"), exist_ok=True)
    path = os.path.join(os.path.dirname(__file__), "..", "results", "oracle_verify.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "mismatch_examples"}, indent=1))


if __name__ == "__main__":
    main()
