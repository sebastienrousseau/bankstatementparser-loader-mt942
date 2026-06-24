<!-- SPDX-License-Identifier: Apache-2.0 -->

# Governance

## Project scope

`bankstatementparser-loader-mt942` is a focused loader companion to the
[`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser)
library. It parses SWIFT MT942 _Interim Transaction Report_ files into
`bankstatementparser` `Transaction` objects. Anything outside that remit
(PDF/CSV parsing, enrichment, exports) lives in the core library or
another companion package.

## Roles

- **Maintainers** — listed in [`MAINTAINERS.md`](MAINTAINERS.md). They
  review and merge PRs, cut releases, and set technical direction.
- **Contributors** — anyone who opens an issue or PR. See
  [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Decision making

- **Routine changes** (bug fixes, test/docs improvements, new tag
  support that fits the existing model) — a single maintainer approval
  is sufficient.
- **Significant changes** (new public API, new runtime dependencies, a
  change to the `Transaction` field mapping) — need explicit lead
  maintainer approval and a CHANGELOG entry.
- Disagreements are resolved by the lead maintainer.

## Becoming a maintainer

We are actively looking for a second maintainer. A track record of
high-quality contributions (well-tested parser fixes, new tag support
with runnable examples) is the path in. Express interest by opening a
discussion.

## Quality bar

Every change must keep the gates green: 100% line + branch test
coverage, 100% docstring coverage (interrogate), `ruff` clean, and
`mypy --strict` clean. Every public function ships a Google-style
docstring, and notable behaviour is covered by a runnable example.
