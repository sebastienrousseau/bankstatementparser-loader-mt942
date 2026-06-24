<!-- SPDX-License-Identifier: Apache-2.0 -->

# Releasing

How to cut a release of `bankstatementparser-loader-mt942`.

## Versioning

This package follows [Semantic Versioning](https://semver.org/). The
single source of truth for the version is
`bankstatementparser_loader_mt942.__version__`; `pyproject.toml` and the
top `CHANGELOG.md` heading must agree. `scripts/verify_versions.py`
enforces this.

- **patch** (`0.0.x`) — bug fixes, docs, tolerated edge cases.
- **minor** (`0.x.0`) — new tags or public API that does not break
  existing callers.
- **major** (`x.0.0`) — breaking changes to the public API or mapping.

## Pre-flight

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install pytest pytest-cov ruff mypy interrogate
pytest --cov=bankstatementparser_loader_mt942 --cov-branch --cov-fail-under=100
ruff check bankstatementparser_loader_mt942 tests examples
mypy bankstatementparser_loader_mt942
interrogate -c pyproject.toml bankstatementparser_loader_mt942
python scripts/verify_versions.py
```

All five must pass.

## Cut the release

1. Bump `__version__` in
   `bankstatementparser_loader_mt942/__init__.py`.
2. Bump `version` in `pyproject.toml` to match.
3. Add a dated `## [X.Y.Z]` section to `CHANGELOG.md`.
4. Run the pre-flight gates above (including `verify_versions.py`).
5. Open a PR; merge once CI is green.
6. Tag the release: `git tag -s vX.Y.Z -m "vX.Y.Z"` and push the tag.
7. The release workflow builds the sdist + wheel and publishes to PyPI
   via Trusted Publishing.

## Supply chain

- **PyPI Trusted Publishing** (OIDC, no long-lived tokens).
- **Sigstore attestations** for sdist + wheel.
- **Signed git tags** on every release.
