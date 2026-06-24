# Provenance — real-world MT942 fixture

This directory holds a **third-party, real-world-format** MT942 file used
to prove the loader handles genuinely messy SWIFT input. It is vendored
byte-for-byte and is **not** edited.

## `centrapay_swift-parser_test2.mt942`

- **Source:** <https://github.com/centrapay/swift-parser> — file
  [`test/test2.mt942`](https://github.com/centrapay/swift-parser/blob/master/test/test2.mt942).
- **Retrieved (verbatim, byte-for-byte):** 2026-06-24 via
  `curl -fsSL https://raw.githubusercontent.com/centrapay/swift-parser/master/test/test2.mt942`.
- **License:** Apache-2.0. Copyright belongs to the upstream
  **centrapay/swift-parser** project and its contributors, not to this
  project. The file is redistributed here under the same Apache-2.0
  license, with attribution preserved per the license terms. See the
  upstream `LICENSE` for the full text.
- **What it is (honest description):** a real-world-**format** MT942
  *interim transaction report* drawn from the `centrapay/swift-parser`
  test corpus. It is third-party test data — **not** a customer export
  from this project's own users, and not produced by this project. It is
  used here purely as an independent, real-world-shaped conformance
  fixture.

### Why it matters

The file is deliberately messy and exercises constructs the loader had to
learn to handle:

- a full **SWIFT message envelope** — `{1:...}{2:...}{4:` ... `-}`;
- **amounts that end on the decimal comma** with no fractional digits
  (`:61:...D5000,` → `Decimal("5000")`, `:34F:NZD0,` → `Decimal("0")`);
- a **`:34F:` floor limit with an embedded D/C indicator** (`NZDC0,`);
- **multi-line `:86:`** information fields (`/BAI/` … `/BENM/` …
  `/ACNO/`);
- a **supplementary-details line right after `:61:`** (`Transfer`,
  `wording/NBKT`).

Its exact parsed output is pinned in `tests/test_real_corpus.py`.
