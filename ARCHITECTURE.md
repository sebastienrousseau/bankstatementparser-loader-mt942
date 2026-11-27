<!-- SPDX-License-Identifier: Apache-2.0 -->

# bankstatementparser-loader-mt942 Architecture

A map of the codebase for new contributors and maintainers. The goal is
that anyone can navigate, extend, and reason about
bankstatementparser-loader-mt942 without prior context.

## The pipeline

```text
MT942 text (string or file)
        |  load_mt942 / load_mt942_file / summarize_mt942
        v
bankstatementparser_loader_mt942/loader.py   (tokeniser + field parsers)
        |  per-line field dicts
        v
bankstatementparser.transaction_models.Transaction.from_record
        v
list[Transaction]  (source="mt942")  /  Mt942Summary
```

The loader is deliberately thin: it tokenises the MT942 tag grammar,
parses each field, and delegates the final object construction to the
core [`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser)
`Transaction.from_record` classmethod. The output is the same
`Transaction` shape the core PDF/CSV parsers produce.

## Module map

| Area | Module | Responsibility |
| :--- | :--- | :--- |
| **Loader** | `bankstatementparser_loader_mt942/loader.py` | Tokeniser, per-tag field parsers, public API, `Mt942StatementParser` |
| **Amounts** | `bankstatementparser_loader_mt942/_amounts.py` | `_comma_decimal`: validates a SWIFT `15d` comma-decimal and converts it to `Decimal` |
| **Package surface** | `bankstatementparser_loader_mt942/__init__.py` | Re-exports the public API and `__version__` |
| **Tests** | `tests/` | 100% line + branch regression suite (`test_loader.py` and focused files for amounts, line endings and debit/credit marks), golden corpora over synthetic and real fixtures, Hypothesis properties (`test_fuzz.py`), docs and examples accuracy, release notes, and the shared suite conformance gate |
| **Fuzzing** | `fuzz/fuzz_load_mt942.py`, `fuzz/corpus/` | Atheris target for `load_mt942` and `summarize_mt942`, run by the CI `Fuzz` job |
| **Benchmarks** | `benches/bench_load_mt942.py` | Load and summary cost as a poll grows; `--quick` runs in CI |
| **Examples** | `examples/` | One runnable script per usage shape |
| **Manual** | `mkdocs.yml`, `docs/` | The MkDocs Material user manual and API reference, deployed to GitHub Pages |
| **Release helpers** | `scripts/` | `verify_versions.py` (`__version__`, `pyproject.toml` and `CHANGELOG.md` agree), `release_notes.py` (release body), `export_locked_requirements.py` (hashed exports of `poetry.lock`), `check_complexity.py` (complexity baseline), `check_suite_consistency.py` (published suite agrees), `readme-check.sh` (README template) |

## Public API

- `load_mt942(text) -> list[Transaction]` — parse from a string.
- `load_mt942_file(path) -> list[Transaction]` — read a file then parse.
- `summarize_mt942(text) -> Mt942Summary` — header metadata + roll-ups.
- `Mt942Summary` — frozen dataclass: `reference`, `account_id`,
  `currency`, `statement_datetime`, `debit_count`, `debit_sum`,
  `credit_count`, `credit_sum`, `transaction_count`.

## Internals

1. **`_iter_fields`** — splits the payload on `:tag:` heads, yielding
   `(tag, value)` pairs. Multi-line values are joined; the trailing `-`
   end-of-message marker and blank lines are absorbed.
2. **Field parsers** — `_parse_line` (`:61:`), `_parse_datetime_stamp`
   (`:13D:`), `_parse_summary` (`:90D:` / `:90C:`), plus the floor-limit
   and amount helpers. SWIFT comma-decimal amounts are validated and
   converted to `Decimal` by `_comma_decimal` (in `_amounts.py`)
   consistently.
3. **`_accumulate`** — threads a mutable `_State` through the field loop,
   then enforces the mandatory `:20:` / `:25:` invariant.
4. **`load_mt942`** — turns each accumulated record into a `Transaction`
   via `Transaction.from_record`, stamping `source="mt942"` and a
   `source_index`.

## Key design decisions

- **Delegation, not duplication.** Object construction is delegated to
  the core `Transaction.from_record`, so the loader never re-implements
  the normalisation, hashing, or field-coercion logic.
- **Postel's law.** Unknown tags are ignored; a malformed `:61:` line is
  skipped rather than fatal; a malformed `:13D:` yields `None`. Only the
  truly mandatory `:20:` / `:25:` fields and malformed `:90x:` summaries
  raise.
- **No invented balances.** MT942 is interim and carries no opening /
  closing balance; the loader never fabricates one.
- **Coverage enforced at 100%** line + branch and docstring.

## Extension points

- **Support a new tag:** add a branch in `_handle_field` and a parser
  helper; pair it with tests in `tests/test_loader.py`.
- **Map a new field:** enrich the per-line record dict in `_parse_line`
  with a key `Transaction.from_record` recognises.

## Where to look first

- Runnable examples: [`examples/`](examples/)
- Roadmap: [`ROADMAP.md`](ROADMAP.md)
- Parent library: [`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser)
