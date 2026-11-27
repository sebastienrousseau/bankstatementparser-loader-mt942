# Benchmarks

`benches/bench_load_mt942.py` measures what an MT942 report costs to
load as it grows along the two axes an intraday poll grows in practice:
transactions within one report (`:61:` lines, each with its `:86:`
narrative) and reports within one poll (several `:20:` blocks
concatenated). It times `load_mt942` and, beside it, `summarize_mt942`,
because a caller that only wants totals should not pay for the full
transaction list.

Nothing asserts a threshold: wall-clock is not comparable between
machines. CI runs `python benches/bench_load_mt942.py --quick` on every
push so the benchmark keeps running against the current API.

## Results

Run with `poetry run python benches/bench_load_mt942.py` on 2026-11-27:
Apple M1 Pro, macOS 27.2.1, CPython 3.12.16,
bankstatementparser-loader-mt942 0.0.36, bankstatementparser 0.0.35.

| Reports | Transactions each | Total | KiB | `load_mt942` ms | `summarize_mt942` ms | us per transaction |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 10 | 10 | 1.0 | 0.16 | 0.05 | 15.67 |
| 1 | 100 | 100 | 8.5 | 1.44 | 0.39 | 14.45 |
| 1 | 1000 | 1000 | 86.7 | 14.67 | 3.90 | 14.67 |
| 10 | 500 | 5000 | 432.8 | 73.05 | 19.49 | 14.61 |
| 50 | 200 | 10000 | 860.5 | 148.67 | 39.64 | 14.87 |

The cost per transaction at 10,000 transactions is 0.95x the cost at
10, so loading is linear: a busy afternoon poll costs in proportion to
its size. `summarize_mt942` costs at most 0.31x `load_mt942`, so the
summary path does not build the transaction list and throw it away.

Reproduce with `python benches/bench_load_mt942.py` (add `--json` for
machine-readable output).
