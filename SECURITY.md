<!-- SPDX-License-Identifier: Apache-2.0 -->

# Security Policy

## Supported versions

Security patches are issued for the latest released `0.0.x`. While
pre-`1.0`, older `0.0.x` versions do not receive security fixes.

| Version | Status | Receives security fixes? |
| :--- | :--- | :--- |
| `0.0.1` (latest) | Current | ✅ Yes |
| _none yet_ | - | - |

## Reporting a vulnerability

**Do not open a public issue for security reports.**

Use GitHub Private Vulnerability Reporting (preferred):
<https://github.com/sebastienrousseau/bankstatementparser-loader-mt942/security/advisories/new>

**Acknowledgement**: within 48 hours. **Triage**: within 7 days.
**Fix windows**: critical 7 days, high 30 days, medium 60 days, low
best-effort.

## Security posture

### Scope

This package exposes the functions `load_mt942(text)`,
`load_mt942_file(path)`, and `summarize_mt942(text)`, which convert a
SWIFT MT942 text payload into `bankstatementparser` `Transaction`
objects (or a summary). It does **not** parse XML, validate against
schemas, or make network calls. `load_mt942_file` reads a single
caller-supplied path and nothing else. Untrusted input is regex-bounded
to a small set of expected MT942 field shapes; a payload missing the
mandatory `:20:` / `:25:` field is rejected with a `ValueError`.

### Threat model

| Surface | How it's handled |
| :--- | :--- |
| **XML / XXE / billion-laughs** | Out of scope. MT942 is a flat text format with no XML envelope. |
| **Catastrophic regex backtracking** | The field regexes are anchored (`^`) and use bounded quantifiers (`\d{6}`, `[A-Z]{3}`, `[CD]`). No nested unbounded groups. |
| **Path traversal** | Only `load_mt942_file` touches the filesystem, opening the exact path the caller supplies. No path is derived from the payload. |
| **Resource exhaustion** | Parsing is O(input size). Callers concerned about hostile input should impose an upstream byte cap. |
| **Bank-specific `:86:` sub-fields** | The value is preserved verbatim as the transaction `description`. The loader does not interpret or execute any embedded content. |
| **Dependency CVEs** | `bankstatementparser >= 0.0.9` is the only runtime dep. Pinned via PyPI and audited by GitHub Dependabot. |

### Cryptography status

This package implements **no** cryptographic functionality. MT942
payloads sometimes arrive in PGP envelopes; decrypt upstream before
passing to this loader.

### Supply chain

- **PyPI Trusted Publishing** (OIDC, no long-lived tokens).
- **Sigstore attestations** for sdist + wheel via
  `pypa/gh-action-pypi-publish`.
- **Signed git tags**: every release tag is signed.
- **No `--no-verify` or `--allow-unverified` shortcuts** in any release
  workflow.

## Contact

- **GitHub Private Vulnerability Reporting (preferred):**
  <https://github.com/sebastienrousseau/bankstatementparser-loader-mt942/security/advisories/new>
