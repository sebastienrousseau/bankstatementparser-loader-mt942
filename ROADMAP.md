<!-- SPDX-License-Identifier: Apache-2.0 -->

# Roadmap

`bankstatementparser-loader-mt942` is intentionally small: parse SWIFT
MT942 into `bankstatementparser` `Transaction` objects, correctly and
without surprises. The roadmap reflects that focus.

Releases stay on the `0.0.x` line, one `0.0.1` step at a time with the
rest of the suite.

## Shipped (0.0.36, current)

- `load_mt942`, `load_mt942_file`, `summarize_mt942`, `Mt942Summary`,
  and `Mt942StatementParser` for the core.
- Full tag coverage: `:20:`, `:25:`, `:28C:`, `:34F:`, `:13D:`, `:61:`,
  `:86:`, `:90D:`, `:90C:`; every SWIFT debit/credit mark (`C`, `D`,
  `RC`, `RD`, `EC`, `ED`) with an optional funds code.
- 100% line + branch + docstring coverage; ruff + mypy strict clean.
- Tested on Linux, macOS and Windows with CPython 3.10 to 3.14; Atheris
  fuzzing of the loader; signed releases with SLSA provenance; a MkDocs
  user manual.

## Considered (future)

- **Bank-specific `:86:` sub-field parsing** (e.g. Deutsche Bank `?20` /
  `?30` / `?32` GVC structured fields) surfaced as structured metadata
  rather than a flat description.
- **Multiple statements per file**: handle a single payload that
  concatenates several MT942 messages, returning one result per message.
- **MT941 (Balance Report)**: a sibling intraday balance message; would
  ship as a separate loader to keep each parser focused.
- **Configurable century window** for `YY` dates, for archival data
  outside the default 1980-2079 range.

Have a need that isn't listed? Open an issue on
[the repository](https://github.com/sebastienrousseau/bankstatementparser-loader-mt942/issues).
