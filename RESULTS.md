# Results

Personal notes on what I measured and how to reproduce it. All runs were on my MacBook (Apple silicon), single thread, Python 3.9.6, with the committed dataset. Raw JSON output of each run is in `results/`.

## Oracle verification, 1M lines

The engine and the independent Decimal-based oracle both computed every one of 1,000,000 seeded random invoice lines (seed 42; roughly 5% use tax transactions, 3% carrying exemption certificates, dates spread over 2022 to 2026, all 120 cities and 22 categories in play). Compared per line: total tax cents plus the full per-jurisdiction breakdown pairs.

```
.venv/bin/python scripts/verify_oracle.py 1000000 42
```

- mismatches: 0 out of 1,000,000
- elapsed: 8.87 s running both implementations on every line (112,767 pair lines/s)

Output: `results/oracle_verify.json`. The suite also keeps a 25k line slice of this comparison in `tests/test_oracle_agreement.py` so it runs on every test invocation.

## Golden invoices

12 hand computed invoices in `golden/golden_invoices.json`, worked out on paper from the committed rate tables before running the engine (the arithmetic is written into each case's notes). All 12 match the engine exactly, including per-jurisdiction breakdowns: `12/12`. They cover origin vs destination sourcing, a rate change straddle, clothing thresholds at one cent below, at, and above the boundary, exact half-cent ties under half_up, half_down and half_even, certificate exemption and expiry, and a use tax accrual.

## Rounding and threshold boundary matrix

`tests/test_boundary_matrix.py` sweeps bases 1 to 4000 cents across 8 rates under all three rounding modes against a Decimal reference (96,000 comparisons), plus every exact half-cent tie at 50 bps for bases up to 100,000 cents (500 ties per mode), plus one cent below / at / one cent above every threshold rule in the matrix. All exact, zero failures.

## Effective date correctness

The same invoice dated 2024-03-31 vs 2024-04-01 (a special district rate change from 22 to 97 bps) produces 843 vs 918 cents of tax, verified down to the per-jurisdiction audit entries. Boundary day lookups, a rate decrease, and a decrease-then-restore sequence are also asserted in `tests/test_effective_dates.py`.

## Throughput

```
.venv/bin/python scripts/bench.py 500000 7
```

- 500,000 lines in 1.711 s: 292,304 lines/s (engine only, invoices pre-generated in memory, single thread)

Output: `results/bench_engine.json`. This includes full audit trail construction per line; it is not a stripped-down fast path.

## API latency

```
.venv/bin/python scripts/bench_api.py 2000
```

In process via the ASGI TestClient (no network hop), 2,000 single line POST /determine requests after a 200 request warmup:

- p50 1.068 ms, p95 1.347 ms, p99 1.551 ms, mean 1.089 ms, 918.4 req/s

Output: `results/bench_api.json`. This measures the app stack (routing, pydantic validation, engine, JSON serialization) but not socket overhead, so treat it as a floor, not a production number.

## Tests and coverage

```
.venv/bin/python -m pytest tests/ --color=no -q --cov=src/taxgrid --cov-report=term-missing
```

- 88 passed, 0 failed
- Coverage: 100% of `src/taxgrid` (294 statements, 0 missed)

## Caveats

The oracle shares the dataset files and my reading of the rules with the engine, so it protects against implementation bugs, not specification misunderstandings; the hand computed goldens are the check on the latter. Timings move a few percent run to run and are specific to this machine. The seeded line generator draws unit prices from 1 cent to 500.00, so very large invoice amounts are only covered by targeted tests, not the randomized million.
