<!-- SPDX-License-Identifier: Apache-2.0 -->

# Getting support

Thanks for using `bankstatementparser-loader-mt942`. Here's the fastest
way to get help, by need.

## Read first

- **[README.md](README.md)** — install, quick start, the supported MT942
  field table, and the `:61:` → `Transaction` mapping.
- **[`examples/`](examples/)** — two runnable scripts exercised in CI.

## Questions & how-to

Open a [GitHub Discussion](https://github.com/sebastienrousseau/bankstatementparser-loader-mt942/discussions)
with:

- Python version + OS
- `bankstatementparser-loader-mt942` version + `bankstatementparser`
  version
- A minimal MT942 payload that reproduces the issue (sensitive values
  redacted)
- The full error output

## Bugs

Open an [issue](https://github.com/sebastienrousseau/bankstatementparser-loader-mt942/issues/new)
with:

- The same triage data as above
- The exact MT942 payload (anonymised) the loader refused to handle
- Expected vs. actual behaviour

## Feature requests

Likely categories:

- **Bank-specific `:86:` sub-fields** (e.g. Deutsche Bank `?20` / `?30`)
  — out of scope for the loader; the raw value is preserved as the
  transaction `description` so you can parse it downstream.
- **MT941 (Balance Report)** — a sibling message; would ship as a
  separate loader. Open an issue to gauge demand.
- **Encrypted MT942** — out of scope; decrypt upstream with `pgp` /
  `gpg` and feed plaintext.

Anything else? Open an issue.

## Security

**Do not** open public issues for vulnerabilities. Follow the private
disclosure process in [SECURITY.md](SECURITY.md).

## Support tiers

This package is open source under Apache-2.0. There is no paid support
tier.

- **Community support** (issues / discussions / PRs): best effort.
- **Commercial support**: not available today.

## Supported versions

| Version | Supported? |
| :--- | :--- |
| 0.0.10 (latest) | ✅ |

Requires Python 3.10+ and `bankstatementparser >= 0.0.9`.
