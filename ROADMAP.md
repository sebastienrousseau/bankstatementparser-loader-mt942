<!-- SPDX-License-Identifier: Apache-2.0 -->

# Roadmap

`bankstatementparser-loader-mt942` is intentionally small: parse SWIFT
MT942 into `bankstatementparser` `Transaction` objects, correctly and
without surprises. The roadmap reflects that focus.

## Shipped — v0.0.1

- `load_mt942`, `load_mt942_file`, `summarize_mt942`, and `Mt942Summary`.
- Full tag coverage: `:20:`, `:25:`, `:28C:`, `:34F:`, `:13D:`, `:61:`,
  `:86:`, `:90D:`, `:90C:`.
- 100% line + branch + docstring coverage; ruff + mypy strict clean.

## Considered — future

- **Bank-specific `:86:` sub-field parsing** (e.g. Deutsche Bank `?20` /
  `?30` / `?32` GVC structured fields) surfaced as structured metadata
  rather than a flat description.
- **Multiple statements per file** — handle a single payload that
  concatenates several MT942 messages, returning one result per message.
- **MT941 (Balance Report)** — a sibling intraday balance message; would
  ship as a separate loader to keep each parser focused.
- **Configurable century window** for `YY` dates, for archival data
  outside the default 1980-2079 range.

Have a need that isn't listed? Open an issue on
[the repository](https://github.com/sebastienrousseau/bankstatementparser-loader-mt942/issues).
