# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-06-24

### Added

- Initial release of `bankstatementparser-loader-mt942`, a loader
  companion to the
  [`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser)
  library that parses SWIFT **MT942 Interim Transaction Report** files —
  a format the core library does not support — into
  `bankstatementparser.transaction_models.Transaction` objects.
- Public API:
  - `load_mt942(text)` — parse an MT942 string into a list of
    `Transaction` objects (`source="mt942"`).
  - `load_mt942_file(path)` — read an MT942 file from disk and parse it.
  - `summarize_mt942(text)` — return an `Mt942Summary` of the message
    metadata and `:90D:` / `:90C:` debit/credit roll-ups.
  - `Mt942Summary` — frozen dataclass with `reference`, `account_id`,
    `currency`, `statement_datetime`, `debit_count`, `debit_sum`,
    `credit_count`, `credit_sum`, and `transaction_count`.
- Supported tags: `:20:` (reference), `:25:` (account id), `:28C:`
  (statement/sequence number), `:34F:` (floor limit, provides the
  currency), `:13D:` (date/time stamp), `:61:` (statement line), `:86:`
  (information to account owner), `:90D:` / `:90C:` (debit/credit
  summaries).
- SWIFT comma-decimal amounts (`500,00`) are converted to exact
  `Decimal` values (`Decimal("500.00")`); debit lines are negated.
- Tolerant parsing: blank lines, the trailing `-` end-of-message marker,
  and unknown tags are ignored; a malformed `:61:` line is skipped; a
  payload missing the mandatory `:20:` or `:25:` field raises a clear
  `ValueError`.
- Runnable examples (`examples/01_load_mt942.py`,
  `examples/02_summarize_mt942.py`), exercised in CI.
- Quality gates pinned at 100% from the initial release:
  - `pytest --cov=bankstatementparser_loader_mt942 --cov-branch
    --cov-fail-under=100` (38 tests, full line + branch coverage).
  - `interrogate --fail-under=100` for module and function docstring
    coverage.
  - `ruff` and `mypy --strict` clean.
- Python 3.10+ support; depends on `bankstatementparser` (>= 0.0.9).

[0.0.1]: https://github.com/sebastienrousseau/bankstatementparser-loader-mt942/releases/tag/v0.0.1
