# bankstatementparser-loader-mt942

**MT942** is SWIFT's _Interim Transaction Report_: the intraday message
a bank sends, often several times a day, with the entries booked on an
account so far. Unlike MT940 it carries no `:60F:` opening or `:62F:`
closing balance; it reports a floor limit, an optional date/time stamp,
the statement lines and debit/credit summaries.

**bankstatementparser-loader-mt942** turns an MT942 payload into a flat
list of
[`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser)
`Transaction` objects (`source="mt942"`), and its `:90D:` / `:90C:`
roll-ups into an `Mt942Summary`.

| Concern | How this loader handles it |
| :--- | :--- |
| Tags | `:20:`, `:25:`, `:28C:`, `:34F:`, `:13D:`, `:61:`, `:86:`, `:90D:`, `:90C:`; unknown tags ignored |
| Amounts | SWIFT comma-decimals (`500,00`) to `Decimal`; a malformed amount is a `ValueError` |
| Debit / credit | `D`, `RC` and `ED` negative; `C`, `RD` and `EC` positive; optional funds code accepted |
| Real-world files | SWIFT `{1:}`...`{4:` envelopes unwrapped, multi-line `:86:` kept, supplementary details folded into the description, CRLF and LF load the same |
| Errors | A clear `ValueError` when `:20:` or `:25:` is missing; a malformed `:61:` line is skipped |

## In this manual

- [MT942 support](format.md): the public API, the tags, the field
  mapping, summaries and errors.
- [The suite](suite.md): the `bankstatementparser` packages.
- [Comparison](COMPARISON.md) and [Benchmarks](BENCHMARKS.md).
- [Supported Python policy](POLICIES.md).
- [API reference](api.md): generated from the docstrings.
- [Roadmap](roadmap.md), [Changelog](changelog.md) and
  [Security policy](security.md).

The source, issues and releases live on
[GitHub](https://github.com/sebastienrousseau/bankstatementparser-loader-mt942);
the package is on
[PyPI](https://pypi.org/project/bankstatementparser-loader-mt942/).
