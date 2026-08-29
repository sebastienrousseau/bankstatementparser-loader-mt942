# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.18] - 2026-08-29

Aligns the `bankstatementparser` suite on one version number, and adds
the scheduled drift check this repository was missing.

### Added

- `scripts/check_suite_consistency.py` and a scheduled `Suite
  Consistency` workflow compare this tree, and every published member of
  the suite, against PyPI. A member left a release behind still installs
  and still passes its own tests; only the index disagrees, and only if
  somebody looks.

### Changed

- Version aligned to `0.0.18` across all six `bankstatementparser`
  packages, which had drifted to `0.0.14`, `0.0.15`, `0.0.17`, `0.0.16`,
  `0.0.16` and `0.0.15`.
- Refreshed the vendored `tests/test_suite_conformance.py` to the current
  canonical copy. Its drift-check probe now matches the bare word `pypi`
  rather than the hostname, which CodeQL read as an incomplete URL
  sanitisation.

## [0.0.16] - 2026-08-29

Brings this repository onto the **suite conformance gate**.

### Added

- **`benches/bench_load_mt942.py`** — MT942 is the intraday report, so
  the same account is parsed again every few minutes, all day, across
  every account being watched. Throughput matters differently from an
  end-of-day statement.

  **Loading is linear** — `us/txn` at 10,000 transactions is 0.72x the
  cost at 10. **`summarize_mt942` costs up to 0.44x `load_mt942`.**

  Worth recording for comparison: MT942 costs roughly **5x more per
  transaction than BAI2** (about 19–23 us against 3–4 us). Different
  formats, different work — but the number is now visible rather than
  assumed.

  Nothing asserts a timing threshold — wall-clock is not comparable
  between machines, and a flaky performance gate teaches people to ignore
  red. CI runs `--quick`, so a benchmark that stops compiling fails the
  build rather than rotting into a file that reads as verified.

- **`tests/test_suite_conformance.py`** — invariants shared by every
  repository in the suite, vendored from one canonical copy and
  checksummed by its own test.

### Changed

- CI lints, formats and runs `benches/` alongside everything else.
- `tomli` (on 3.10) and `packaging` are named as dev dependencies; the
  conformance gate parses `pyproject.toml` and needs both.
- `tests/test_suite_conformance.py` is excluded from black: it is
  generated, and the suite uses three different line lengths.

## [0.0.15] - 2026-08-28

### Changed

- **A plain `pytest` now enforces the same 100% coverage floor CI does.**
  `--cov`, `--cov-branch` and `--cov-report=term-missing` move into
  `[tool.pytest.ini_options] addopts`. Before this, running `pytest`
  locally measured no coverage at all: the developer saw green and learned
  otherwise from the build.

  The gate itself was never missing — CI has always run
  `--cov-fail-under=100`, so nothing could regress onto `main` unnoticed.
  What was missing was the local half of it.

- **The floor is stated once.** It was in two places, the
  `--cov-fail-under` flag in `ci.yml` and `fail_under` under
  `[tool.coverage.report]`, which is how two numbers meant to be equal stop
  being equal. pytest-cov honours `fail_under` from the coverage config, so
  the flag is gone from both `addopts` and the workflow and the number lives
  in exactly one place.

  CI now runs `pytest tests/ --cov-report=xml -v`; only the XML report is
  CI-specific.

### Verification

Coverage was already 100% and remains so. The gate was mutation-tested:
adding a function no test calls drops coverage below the floor and fails
the run, locally as well as in CI.

## [0.0.14] - 2026-07-18

### Changed

- chore(deps): require `bankstatementparser>=0.0.11` (was `>=0.0.9`),
  keeping the loader in lockstep with the 0.0.11 core release. No
  functional or API changes.

## [0.0.13] - 2026-06-25

### Changed

- **Audit pass.** Linked `tests/fixtures/real/PROVENANCE.md` from the README so the vendored real-world fixture's source/license is discoverable.

## [0.0.12] - 2026-06-24

### Added

- A **real-world-format, third-party MT942 fixture**,
  `tests/fixtures/real/centrapay_swift-parser_test2.mt942`, vendored
  byte-for-byte from the Apache-2.0 `centrapay/swift-parser` test corpus
  (provenance and licensing in `tests/fixtures/real/PROVENANCE.md`). It is
  genuinely messy and exercises constructs the synthetic fixtures did not.
- A **golden test for the real file** (`tests/test_real_corpus.py`) that
  pins the exact parsed `Transaction` list (signed `Decimal` amounts,
  dates, multi-line `:86:` descriptions, currency, `account_id`,
  transaction id and reference) and the full nine-field `Mt942Summary` —
  the proof the messy real file parses correctly. `load_mt942`,
  `load_mt942_file`, `summarize_mt942` and `Mt942Summary` are all
  exercised against it.
- **Mutation testing** with `mutmut` (`make mutation`, `[tool.mutmut]`
  config) as a rigorous answer to "100% line coverage is weak evidence".
  Final score: **348/355 mutants killed (97.7%)**; the 7 survivors are
  all genuine *equivalent mutants*, each justified in
  `tests/MUTATION.md`. New targeted tests were added to kill every
  non-equivalent survivor.

### Fixed

- **SWIFT message envelope** is now stripped before parsing. Real MT942
  messages wrap the body in header blocks `{1:...}{2:...}` and a text
  block `{4:` … `-}`. Previously the trailing `-}` was glued onto the
  last field value (a malformed `:90C:` field, raising `ValueError`) and
  header lines risked being misread; now the envelope is removed and the
  `:tag:` body parses cleanly.
- **Amounts ending on the decimal comma with no fractional digits** are
  accepted: `:61:…D5000,` → `Decimal("5000")` and `:34F:NZD0,` →
  `Decimal("0")`. (These already round-tripped through `Decimal`, now
  pinned by tests.)
- **`:34F:` floor limit with an embedded D/C indicator** (`:34F:NZDC0,`)
  parses the currency correctly regardless of the indicator.
- **Multi-line `:86:`** continuation lines (e.g. `/BAI/…`, `/BENM/…`,
  `/ACNO/…`) are appended to the transaction `description`,
  newline-separated.
- **Supplementary-details line right after `:61:`** (e.g. a bare
  `Transfer` or `wording/NBKT` before the `:86:`) is no longer glued onto
  the statement-line tail — which previously **corrupted the reference**
  (`NTRFNONREF` became `NTRFNONREFTransfer`). It is now captured as the
  SWIFT supplementary-details subfield and folded into the description
  (supplementary text first, then the `:86:` content, joined by
  newlines); a `:61:` with supplementary details but no following `:86:`
  keeps that text as its description. The public API is unchanged.

### Changed

- Trimmed heavy CI for a small parsing library: removed the `codeql.yml`
  and `security.yml` workflows (and `.github/codeql/`). The retained
  workflows are `ci.yml`, `pr.yml`, and `release.yml`.

## [0.0.11] - 2026-06-24

### Added

- An expanded real-world MT942 test corpus under `tests/fixtures/`, with
  three additional realistic samples that differ in genuine wire-format
  detail: `:61:` lines with and without the optional 4-digit entry
  (booking) date; one versus two `:34F:` floor-limit lines (debit and
  credit floor); `:13D:` present versus absent; several `:61:`/`:86:`
  transactions of mixed credit/debit; and trailing `-` end-of-message
  markers with stray blank lines.
- Golden-style tests (`tests/test_corpus.py`) that pin the **exact**
  parsed `Transaction` list (amount sign and `Decimal` value, value and
  booking dates, description, `account_id`, currency, transaction id and
  reference) and the full nine-field `Mt942Summary` (`reference`,
  `account_id`, `currency`, `statement_datetime`, `debit_count`,
  `debit_sum`, `credit_count`, `credit_sum`, `transaction_count`) for
  every fixture, so a parsing regression can never pass silently.
- An install **smoke test** job (`smoke`) in CI: it builds the wheel,
  installs it into a fresh virtual environment (pulling
  `bankstatementparser` from PyPI), imports the package and prints
  `__version__`, then runs `examples/01_load_mt942.py` from a neutral
  working directory — proving the published artifact installs and works
  outside the source tree. The flow is reproducible locally.

### Changed

- Pruned over-scaffolded CI: removed the `nightly.yml` and `docs.yml`
  workflows. The retained workflows are `ci.yml`, `pr.yml`, `codeql.yml`,
  `security.yml`, and `release.yml`. (This is a library, so there is no
  `docker.yml`.) The public API is unchanged.

## [0.0.10] - 2026-06-24

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
- Regression and documentation-accuracy test suites:
  - `tests/test_regression_examples.py` runs every `examples/*.py`
    script as a subprocess and asserts a clean (`0`) exit.
  - `tests/test_regression_docs.py` executes every fenced `python`
    block in `README.md` in-process via a `BLOCK_SPECS` registry, so a
    documented snippet can never silently rot.
  - `tests/test_docs_accuracy.py` asserts the README version/badge,
    public-symbol coverage, example paths, and numeric/field claims all
    match the code.
- Quality gates pinned at 100% from the initial release:
  - `pytest --cov=bankstatementparser_loader_mt942 --cov-branch
    --cov-fail-under=100` (full line + branch coverage).
  - `interrogate --fail-under=100` for module and function docstring
    coverage.
  - `ruff` and `mypy --strict` clean.
- Python 3.10+ support; depends on `bankstatementparser` (>= 0.0.9).

[0.0.11]: https://github.com/sebastienrousseau/bankstatementparser-loader-mt942/releases/tag/v0.0.11
[0.0.10]: https://github.com/sebastienrousseau/bankstatementparser-loader-mt942/releases/tag/v0.0.10
