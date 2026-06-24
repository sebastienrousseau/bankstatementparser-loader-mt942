# bankstatementparser-loader-mt942: SWIFT MT942 loader

[![PyPI Version][pypi-badge]][pypi-url]
[![Python Versions][python-versions-badge]][pypi-url]
[![License][license-badge]][license-url]
[![Tests][tests-badge]][tests-url]
[![Quality][quality-badge]][tests-url]

**Parse SWIFT MT942 _Interim Transaction Report_ files into
[`bankstatementparser`][core] `Transaction` objects.** A single
`load_mt942(text)` call returns a list of
`bankstatementparser.transaction_models.Transaction`, ready for every
downstream consumer that already works with the core library's parser
output (deduplication, categorisation, exports).

> The core [`bankstatementparser`][core] library parses PDF and CSV
> statements but does **not** understand the SWIFT MT942 wire format.
> This loader fills that gap without changing the core data model.

## Contents

- [Overview](#overview)
- [Install](#install)
- [Quick Start](#quick-start)
- [Supported Fields](#supported-fields)
- [Field Mapping](#field-mapping)
- [Summaries](#summaries)
- [Errors](#errors)
- [Examples](#examples)
- [When not to use this loader](#when-not-to-use-this-loader)
- [Development](#development)
- [Security](#security)
- [Documentation](#documentation)
- [License](#license)
- [Contributing](#contributing)
- [Acknowledgements](#acknowledgements)

## Overview

`bankstatementparser-loader-mt942` is a small, focused companion to the
[`bankstatementparser`][core] library. It does one thing well: parse the
SWIFT MT942 _Interim Transaction Report_ grammar and hand back the same
`Transaction` objects the core PDF/CSV parsers produce. Every
transaction is stamped with `source="mt942"` so you can tell where it
came from.

MT942 is an **interim** statement. Unlike MT940 it carries **no** `:60F:`
opening or `:62F:` closing balance — it reports a floor limit, an
optional date/time stamp, the statement lines accumulated so far, and
debit/credit summaries. This loader models that structure faithfully and
never invents balances that are not present in the source.

## Install

`bankstatementparser-loader-mt942` runs on macOS, Linux, and Windows and
requires **Python 3.10+** and **pip**. It pulls in
[`bankstatementparser`][core] (>= 0.0.9) automatically.

```bash
pip install bankstatementparser-loader-mt942
```

## Quick Start

```python
from bankstatementparser_loader_mt942 import load_mt942

mt942 = """:20:MT942REF001
:25:COBADEFFXXX/DE89370400440532013000
:28C:42/1
:34F:EURD0,00
:34F:EURC0,00
:13D:2506241200+0100
:61:2506240624C500,00NTRFINV-123//BANKREF1
:86:Incoming payment for invoice 123
:61:2506240624D200,50NTRFRENT//BANKREF2
:86:Monthly rent debit
:90D:1EUR200,50
:90C:1EUR500,00
-
"""

transactions = load_mt942(mt942)

for txn in transactions:
    print(txn.value_date, txn.currency, txn.amount, txn.description)
# 2025-06-24 EUR 500.00 Incoming payment for invoice 123
# 2025-06-24 EUR -200.50 Monthly rent debit
```

Those are `bankstatementparser.transaction_models.Transaction` objects —
debit lines carry a **negative** amount, credit lines a **positive** one,
and amounts are exact `Decimal` values (SWIFT's comma decimal separator
`500,00` is converted to `Decimal("500.00")`).

To read from a file instead of a string:

```python
from bankstatementparser_loader_mt942 import load_mt942_file

transactions = load_mt942_file("statement.mt942")
```

## Supported Fields

| Tag | Meaning | Cardinality |
| :--- | :--- | :--- |
| `:20:` | Transaction reference number | mandatory |
| `:25:` | Account identification (the account id) | mandatory |
| `:28C:` | Statement / sequence number | optional |
| `:34F:` | Floor limit indicator `<CCY>[D\|C]<amount>` (provides the currency) | one or two |
| `:13D:` | Date/time stamp `YYMMDDHHMM±HHMM` | optional |
| `:61:` | Statement line (one per booked entry) | repeatable |
| `:86:` | Information to account owner (attaches to the preceding `:61:`) | optional, per line |
| `:90D:` | Debit summary `<count><CCY><amount>` | optional |
| `:90C:` | Credit summary `<count><CCY><amount>` | optional |

Unrecognised tags (and the trailing `-` end-of-message marker) are
**silently ignored**, so future SWIFT additions do not break parsing —
this follows Postel's law: be liberal in what you accept. A malformed
`:61:` statement line is **skipped** rather than fatal, so one bad row
never aborts the whole parse.

### Real-world wire-format constructs

Genuine bank/SWIFT exports are messier than the tidy sample above. The
loader handles the following (pinned by a golden test over a real,
third-party fixture in `tests/fixtures/real/`):

- **SWIFT message envelope.** Messages wrapped in the header blocks
  `{1:...}{2:...}{3:...}` and the text block `{4:` … `-}` are unwrapped
  before parsing; the envelope is never mistaken for content.
- **Amounts with no fractional digits.** A SWIFT amount may end on the
  decimal comma with nothing after it: `5000,` → `Decimal("5000")`,
  `0,` → `Decimal("0")`.
- **`:34F:` with an embedded D/C indicator.** `:34F:NZDC0,` yields
  currency `NZD` regardless of the `C`/`D` letter.
- **Multi-line `:86:`.** Continuation lines that do not start with a
  `:tag:` head (e.g. `/BAI/…`, `/BENM/…`, `/ACNO/…`) are appended to the
  `:86:` description, newlines preserved.
- **Supplementary details after `:61:`.** A line immediately following a
  `:61:` (before any `:86:`), such as a bare `Transfer` or
  `wording/NBKT`, is the SWIFT supplementary-details subfield. It is
  **folded into the transaction's `description`** (supplementary text
  first, then the `:86:` content, joined by newlines) and never glued
  onto the statement-line tail — so the parsed `transaction_id` /
  `reference` stay clean. A `:61:` with supplementary details but no
  following `:86:` keeps that text as its description.

## Field Mapping

Each `:61:` statement line becomes one `Transaction`:

| `Transaction` field | Source |
| :--- | :--- |
| `account_id` | `:25:` |
| `currency` | `:34F:` |
| `amount` | `:61:` amount, negated for debit (`D`) lines, as `Decimal` |
| `value_date` | `:61:` value date (`YYMMDD`) |
| `booking_date` | `:61:` optional entry date (`MMDD`, inherits the value-date year) |
| `transaction_id` | the bank reference in the `:61:` tail (left of `//`) |
| `reference` | the customer reference in the `:61:` tail (right of `//`) |
| `description` | the following `:86:` free-form text |
| `source` | always `"mt942"` |
| `source_index` | the zero-based line index within the message |

The two-digit `YY` year uses the standard SWIFT sliding window: `00`-`79`
map to `20YY`, `80`-`99` to `19YY`.

## Summaries

When you want the message metadata and the `:90D:`/`:90C:` roll-ups
rather than the individual transactions, call `summarize_mt942`:

```python
from bankstatementparser_loader_mt942 import summarize_mt942

summary = summarize_mt942(mt942)
print(summary.reference)          # MT942REF001
print(summary.currency)           # EUR
print(summary.debit_count)        # 1
print(summary.debit_sum)          # Decimal("200.50")
print(summary.credit_sum)         # Decimal("500.00")
print(summary.transaction_count)  # 2
```

`Mt942Summary` is a frozen dataclass with `reference`, `account_id`,
`currency`, `statement_datetime`, `debit_count`, `debit_sum`,
`credit_count`, `credit_sum`, and `transaction_count`. Optional fields
(no `:90x:` / `:13D:` present) default to `None`.

## Errors

A payload missing the mandatory `:20:` reference or `:25:` account
identification raises `ValueError` with a message naming the missing tag:

```python
load_mt942(":25:ACC\n:61:250624C10,00NTRFX\n")
# ValueError: MT942 payload missing required :20: reference
```

## Examples

Two runnable examples live in [`examples/`](examples/):

- [`01_load_mt942.py`](examples/01_load_mt942.py) — parse a small MT942
  string into transactions.
- [`02_summarize_mt942.py`](examples/02_summarize_mt942.py) — read a file
  and print the `Mt942Summary` roll-ups.

Both are exercised in CI on every commit.

## When not to use this loader

- **You have a PDF or CSV statement.** Use the core
  [`bankstatementparser`][core] parsers directly — this loader is only
  for the SWIFT MT942 wire format.
- **You have MT940 (final statements with balances).** MT940 is a
  different message; this loader handles the interim MT942 report. The
  `:61:` / `:86:` grammar is shared, but MT942 has no `:60F:` / `:62F:`
  balances.
- **You need bank-specific `:86:` sub-field parsing** (e.g. Deutsche
  Bank's `?20` / `?30` / `?32` GVC codes). The raw `:86:` value is
  preserved verbatim as the transaction `description`; downstream tooling
  can parse it if needed.
- **Your MT942 is PGP / GPG encrypted.** Decrypt upstream and pass the
  plaintext to the loader.

## Development

```bash
git clone https://github.com/sebastienrousseau/bankstatementparser-loader-mt942
cd bankstatementparser-loader-mt942
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install pytest pytest-cov ruff mypy interrogate
pytest --cov=bankstatementparser_loader_mt942 --cov-branch --cov-fail-under=100
ruff check bankstatementparser_loader_mt942 tests examples
mypy bankstatementparser_loader_mt942
interrogate -c pyproject.toml bankstatementparser_loader_mt942
```

## Security

`bankstatementparser-loader-mt942` parses a flat text format with no XML
envelope, so the XXE / billion-laughs surface does not apply. Field
regexes are anchored and bounded, so catastrophic backtracking is not a
concern. Reporting practice and supported versions are documented in
[`SECURITY.md`](SECURITY.md). Vulnerabilities go via GitHub Private
Vulnerability Reporting, not public issues.

## Documentation

- [`README.md`](README.md) — this file
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — codebase map
- [`CHANGELOG.md`](CHANGELOG.md) — release notes
- [`ROADMAP.md`](ROADMAP.md) — what's next
- [`SECURITY.md`](SECURITY.md) — disclosure + supported versions
- [`examples/`](examples/) — runnable scripts, exercised in CI

## License

Licensed under the [Apache License, Version 2.0][license-url]. Any
contribution submitted for inclusion shall be licensed as above, without
additional terms.

## Contributing

Contributions are welcome. Open an issue or PR on
[the repository](https://github.com/sebastienrousseau/bankstatementparser-loader-mt942).

## Acknowledgements

Built on the [`bankstatementparser`][core] library. The MT942 grammar
follows the SWIFT User Handbook MT942 _Interim Transaction Report_
specification and the common-denominator subset shipped by major EU and
UK commercial banks.

[core]: https://github.com/sebastienrousseau/bankstatementparser
[pypi-url]: https://pypi.org/project/bankstatementparser-loader-mt942/
[license-url]: https://opensource.org/license/apache-2-0/
[tests-url]: https://github.com/sebastienrousseau/bankstatementparser-loader-mt942/actions/workflows/ci.yml
[pypi-badge]: https://img.shields.io/pypi/v/bankstatementparser-loader-mt942.svg?style=for-the-badge
[python-versions-badge]: https://img.shields.io/pypi/pyversions/bankstatementparser-loader-mt942.svg?style=for-the-badge
[license-badge]: https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge
[tests-badge]: https://img.shields.io/github/actions/workflow/status/sebastienrousseau/bankstatementparser-loader-mt942/ci.yml?branch=main&label=Tests&style=for-the-badge
[quality-badge]: https://img.shields.io/badge/Coverage-100%25-brightgreen?style=for-the-badge
