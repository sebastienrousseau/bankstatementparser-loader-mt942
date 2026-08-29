#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""What an MT942 interim report costs to load, as it grows.

MT942 is the intraday report: a bank sends it repeatedly through the day,
and a treasury system polls it on a timer. That makes throughput matter
differently from an end-of-day statement — the same account is parsed
again every few minutes, all day, across every account being watched.

Two axes move in practice, so both are measured:

* **Transactions within one report** (``:61:`` lines, each with its
  ``:86:`` narrative).
* **Reports within one poll** (several ``:20:`` blocks concatenated, which
  is how a multi-account poll arrives).

Read ``us/txn``. Flat means linear, and a busy afternoon poll is fine.
Climbing means something rescans records it has already read — invisible
on the small fixtures, obvious on a real file.

``summarize_bai2`` is measured beside ``load_bai2`` because callers that
only want totals should not have to pay for the full transaction list. If
the two cost the same, the summary is building everything and then
discarding it, and the cheap path is not actually cheap.

Run::

    python benches/bench_load_mt942.py
    python benches/bench_load_mt942.py --json
    python benches/bench_load_mt942.py --quick     # what CI runs

Nothing here asserts a threshold: wall-clock is not comparable between
machines, and a flaky performance gate teaches people to ignore red. CI
runs ``--quick`` so a benchmark that has stopped compiling against the
current API fails the build instead of rotting into a file that reads as
verified and is not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bankstatementparser_loader_mt942 import (  # noqa: E402
    load_mt942,
    summarize_mt942,
)

HEADER = """:20:MT942-BENCH-{n}
:25:COBADEFFXXX/DE89370400440532013000
:28C:{n}/1
:34F:EURD0,00
:34F:EURC0,00
:13D:2506241200+0100
"""

TXN = """:61:2506240624C{amount},00NTRFINV-{i}//BANKREF{i}
:86:Benchmark narrative for transaction {i}
"""

TAIL = """:90D:0EUR0,00
:90C:{count}EUR{total},00
-
"""


def build(reports: int, txns_each: int) -> str:
    """``reports`` MT942 reports of ``txns_each`` transactions each."""
    parts = []
    for n in range(reports):
        parts.append(HEADER.format(n=n))
        total = 0
        for i in range(txns_each):
            amount = (i % 900) + 100
            total += amount
            parts.append(TXN.format(amount=amount, i=i))
        parts.append(TAIL.format(count=txns_each, total=total))
    return "".join(parts)


def _best(call, repeats: int) -> float:
    """Best-of timing after one untimed warm-up.

    The minimum is the least noisy estimator available; the mean follows
    whatever else the machine happens to be doing.
    """
    call()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        samples.append(time.perf_counter() - start)
    return min(samples)


def measure(reports: int, txns_each: int, repeats: int) -> dict:
    text = build(reports, txns_each)
    load = _best(lambda: load_mt942(text), repeats)
    summary = _best(lambda: summarize_mt942(text), repeats)
    transactions = len(load_mt942(text))
    return {
        "reports": reports,
        "txns_each": txns_each,
        "transactions": transactions,
        "bytes": len(text),
        "load_ms": load * 1e3,
        "summary_ms": summary * 1e3,
        "us_per_txn": load * 1e6 / transactions if transactions else 0.0,
        "summary_over_load": summary / load if load else 0.0,
    }


def run(quick: bool) -> list[dict]:
    if quick:
        shapes = [(1, 10), (1, 100)]
        repeats = 3
    else:
        shapes = [(1, 10), (1, 100), (1, 1_000), (10, 500), (50, 200)]
        repeats = 7
    return [measure(r, t, repeats) for r, t in shapes]


def render(rows: list[dict]) -> None:
    print(
        f"{'reports':>9}{'txns each':>11}{'total':>8}{'KiB':>9}"
        f"{'load ms':>10}{'summary ms':>12}{'us/txn':>9}"
    )
    for row in rows:
        print(
            f"{row['reports']:>9}{row['txns_each']:>11}"
            f"{row['transactions']:>8}{row['bytes'] / 1024:>9.1f}"
            f"{row['load_ms']:>10.2f}{row['summary_ms']:>12.2f}"
            f"{row['us_per_txn']:>9.2f}"
        )
    if len(rows) >= 2 and rows[0]["us_per_txn"]:
        drift = rows[-1]["us_per_txn"] / rows[0]["us_per_txn"]
        print(
            f"\n  us/txn at {rows[-1]['transactions']:,} transactions is "
            f"{drift:.2f}x the cost at {rows[0]['transactions']:,}. Flat is "
            f"linear, and a busy afternoon poll is fine. Climbing means "
            f"something rescans records it has already read."
        )
    ratios = [r["summary_over_load"] for r in rows if r["summary_over_load"]]
    if ratios:
        worst = max(ratios)
        print(
            f"\n  summarize_mt942 costs up to {worst:.2f}x load_mt942. A "
            f"caller that only wants totals should pay less than one that "
            f"wants every transaction; a ratio near 1.00 means the summary "
            f"builds the full list and then throws it away."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--quick", action="store_true", help="small sizes, as CI runs"
    )
    args = parser.parse_args()

    rows = run(quick=args.quick)
    if args.json:
        json.dump(rows, sys.stdout, indent=1)
        print()
    else:
        render(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
