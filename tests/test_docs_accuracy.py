# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Automated validation that README, docs, and examples stay in sync
with the actual code.

If any of these tests fail, a markdown file carries a stale claim a
human will trust and act on. Fix the docs (or the code), not the test.
The companion ``test_regression_docs.py`` *executes* the README code
blocks; this module checks the *prose* claims around them.
"""

from __future__ import annotations

import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

import bankstatementparser_loader_mt942 as pkg
from bankstatementparser_loader_mt942 import summarize_mt942

# ---------------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
EXAMPLES_README = REPO_ROOT / "examples" / "README.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"

SRC_DIR = REPO_ROOT / "bankstatementparser_loader_mt942"
EXAMPLES_DIR = REPO_ROOT / "examples"

# These tests assert that the repo-root docs (README/CHANGELOG/examples)
# stay in sync with the code. Under mutmut the suite runs from a
# ``mutants/`` sandbox copy that contains only the package and tests, not
# the docs; skip there cleanly (doc sync is out of scope for mutation
# testing of loader logic).
pytestmark = pytest.mark.skipif(
    not (REPO_ROOT / "README.md").exists(),
    reason="docs absent (mutmut sandbox): doc-sync checks not applicable",
)

#: Every public symbol the package promises via ``__all__``.
PUBLIC_SYMBOLS = (
    "load_mt942",
    "load_mt942_file",
    "summarize_mt942",
    "Mt942Summary",
)


def _read(path: Path) -> str:
    """Return the UTF-8 text of ``path``.

    Args:
        path: The file to read.

    Returns:
        The file contents decoded as UTF-8.
    """
    return path.read_text(encoding="utf-8")


def _pyproject_version() -> str:
    """Return the version string declared in ``pyproject.toml``.

    Returns:
        The ``[tool.poetry] version`` value.
    """
    match = re.search(
        r'^version\s*=\s*"([^"]+)"', _read(PYPROJECT), re.MULTILINE
    )
    assert match is not None, "pyproject.toml has no version field"
    return match.group(1)


# ---------------------------------------------------------------------------
# 1. Version consistency: badge == pyproject == __version__
# ---------------------------------------------------------------------------


class TestVersionConsistency:
    """The version string agrees across package, pyproject, and docs."""

    def test_package_version_matches_pyproject(self) -> None:
        """``__version__`` equals the pyproject version."""
        assert pkg.__version__ == _pyproject_version()

    def test_changelog_has_current_version_entry(self) -> None:
        """CHANGELOG has a heading for the current version."""
        version = _pyproject_version()
        assert f"[{version}]" in _read(
            CHANGELOG
        ), f"CHANGELOG.md has no entry for current version {version}"

    def test_verify_versions_script_passes(self) -> None:
        """The shipped ``scripts/verify_versions.py`` exits 0."""
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "verify_versions.py"),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_python_version_matches_pyproject(self) -> None:
        """The README documents the Python floor declared in pyproject."""
        if ">=3.10" in _read(PYPROJECT):
            assert "3.10" in _read(
                README
            ), "README should mention the Python 3.10 minimum"

    def test_core_dependency_floor_matches_pyproject(self) -> None:
        """The README states the same core-library floor as pyproject."""
        match = re.search(
            r'bankstatementparser\s*=\s*">=([0-9.]+)', _read(PYPROJECT)
        )
        assert match is not None, "pyproject has no bankstatementparser pin"
        assert match.group(1) in _read(
            README
        ), f"README should mention core floor >= {match.group(1)}"


# ---------------------------------------------------------------------------
# 2. Public API surface documented
# ---------------------------------------------------------------------------


class TestApiSurface:
    """Every public symbol is exported and documented."""

    def test_all_exports_importable(self) -> None:
        """Every name in ``__all__`` is a real attribute of the package."""
        assert set(pkg.__all__) == set(PUBLIC_SYMBOLS)
        for name in pkg.__all__:
            assert hasattr(pkg, name), f"{name} missing from package"

    def test_every_public_symbol_in_readme(self) -> None:
        """Every public symbol is documented somewhere in the README."""
        readme = _read(README)
        for name in PUBLIC_SYMBOLS:
            assert (
                name in readme
            ), f"README does not document public symbol {name!r}"

    def test_summary_fields_documented(self) -> None:
        """Every ``Mt942Summary`` field name appears in the README."""
        import dataclasses

        readme = _read(README)
        for fld in dataclasses.fields(pkg.Mt942Summary):
            assert (
                fld.name in readme
            ), f"README does not document Mt942Summary.{fld.name}"


# ---------------------------------------------------------------------------
# 3. Referenced example paths exist
# ---------------------------------------------------------------------------


class TestExamplesExist:
    """Every example path referenced in the docs exists on disk."""

    def _referenced_scripts(self, text: str) -> list[str]:
        """Pull ``examples/*.py`` script names out of markdown.

        Args:
            text: The markdown source to scan.

        Returns:
            The example script basenames referenced in the text.
        """
        return re.findall(r"`(\d+_[\w]+\.py)`", text)

    def test_readme_example_paths_exist(self) -> None:
        """Every example referenced in README.md exists."""
        scripts = self._referenced_scripts(_read(README))
        assert scripts, "README references no example scripts"
        for script in scripts:
            assert (
                EXAMPLES_DIR / script
            ).exists(), (
                f"README references examples/{script} but it is missing"
            )

    def test_examples_readme_paths_exist(self) -> None:
        """Every example referenced in examples/README.md exists."""
        scripts = self._referenced_scripts(_read(EXAMPLES_README))
        assert scripts, "examples/README.md references no scripts"
        for script in scripts:
            assert (
                EXAMPLES_DIR / script
            ).exists(), (
                f"examples/README.md references {script} but it is missing"
            )

    def test_readme_example_count_matches_disk(self) -> None:
        """The README claim about the number of examples is accurate."""
        on_disk = sorted(
            p.name
            for p in EXAMPLES_DIR.glob("*.py")
            if "__pycache__" not in str(p)
        )
        match = re.search(r"(\w+) runnable examples? live", _read(README))
        assert match is not None, "README should state how many examples ship"
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        claimed = words.get(match.group(1).lower())
        if claimed is None:
            claimed = int(match.group(1))
        assert claimed == len(on_disk), (
            f"README claims {claimed} examples but {len(on_disk)} ship: "
            f"{on_disk}"
        )

    def test_example_scripts_compile(self) -> None:
        """Every example passes py_compile (no syntax errors)."""
        for py in sorted(EXAMPLES_DIR.glob("*.py")):
            if "__pycache__" in str(py):
                continue
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(py)],
                capture_output=True,
                text=True,
            )
            assert (
                result.returncode == 0
            ), f"{py.name} has syntax errors: {result.stderr}"


# ---------------------------------------------------------------------------
# 4. Numeric / field claims match real parser behaviour
# ---------------------------------------------------------------------------

#: The exact MT942 used in the README Quick Start and Summaries blocks.
_README_SAMPLE = """:20:MT942REF001
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


class TestNumericClaims:
    """The numbers the README prints in comments match the parser."""

    def test_readme_sample_block_is_present_verbatim(self) -> None:
        """The README really contains the exact sample used below."""
        readme = _read(README)
        for line in (
            ":20:MT942REF001",
            ":34F:EURD0,00",
            ":61:2506240624C500,00NTRFINV-123//BANKREF1",
            ":90C:1EUR500,00",
        ):
            assert line in readme, f"README sample drifted: {line!r} absent"

    def test_summary_claims_match_parser(self) -> None:
        """Each ``summary.x`` comment in the README is the real value."""
        summary = summarize_mt942(_README_SAMPLE)
        assert summary.reference == "MT942REF001"
        assert summary.currency == "EUR"
        assert summary.debit_count == 1
        assert summary.debit_sum == Decimal("200.50")
        assert summary.credit_sum == Decimal("500.00")
        assert summary.transaction_count == 2

        readme = _read(README)
        # The README annotates each print with the expected output.
        assert "# MT942REF001" in readme
        assert "# EUR" in readme
        assert 'Decimal("200.50")' in readme
        assert 'Decimal("500.00")' in readme

    def test_source_tag_claim_is_accurate(self) -> None:
        """The README claim of ``source="mt942"`` matches the parser."""
        from bankstatementparser_loader_mt942 import load_mt942

        txns = load_mt942(_README_SAMPLE)
        assert all(t.source == "mt942" for t in txns)
        assert 'source="mt942"' in _read(README)

    def test_debit_negation_claim_is_accurate(self) -> None:
        """Debit lines are negative and credit lines positive, as claimed."""
        from bankstatementparser_loader_mt942 import load_mt942

        credit, debit = load_mt942(_README_SAMPLE)
        assert credit.amount == Decimal("500.00")
        assert debit.amount == Decimal("-200.50")

    def test_module_count_claim(self) -> None:
        """If the README claims a module count, it must be accurate."""
        modules = [
            p for p in SRC_DIR.rglob("*.py") if "__pycache__" not in str(p)
        ]
        match = re.search(r"(\d+)\s+modules", _read(README))
        if match is not None:
            assert int(match.group(1)) == len(modules), (
                f"README claims {match.group(1)} modules but "
                f"{len(modules)} exist"
            )

    def test_test_count_claim_if_present(self) -> None:
        """If the README states a test count, it must match reality."""
        actual = 0
        for py in (REPO_ROOT / "tests").rglob("*.py"):
            actual += len(
                re.findall(r"^\s*def test_", _read(py), re.MULTILINE)
            )
        for claimed in re.findall(r"\b(\d+)\s+tests\b", _read(README)):
            assert (
                int(claimed) == actual
            ), f"README claims {claimed} tests but {actual} exist"


# ---------------------------------------------------------------------------
# 5. CHANGELOG accuracy
# ---------------------------------------------------------------------------


class TestChangelogAccuracy:
    """CHANGELOG numeric claims match the codebase."""

    def test_changelog_test_count_matches_reality(self) -> None:
        """Any ``N tests`` claim in the CHANGELOG matches the real count."""
        actual = 0
        for py in (REPO_ROOT / "tests").rglob("*.py"):
            actual += len(
                re.findall(r"^\s*def test_", _read(py), re.MULTILINE)
            )
        for claimed in re.findall(r"\b(\d+)\s+tests\b", _read(CHANGELOG)):
            assert (
                int(claimed) == actual
            ), f"CHANGELOG claims {claimed} tests but {actual} exist"

    def test_changelog_documents_every_public_symbol(self) -> None:
        """The CHANGELOG release notes name every public symbol."""
        changelog = _read(CHANGELOG)
        for name in PUBLIC_SYMBOLS:
            assert (
                name in changelog
            ), f"CHANGELOG does not mention public symbol {name!r}"
