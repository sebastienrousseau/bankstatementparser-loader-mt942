# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Regression suite: execute every shipped example script end-to-end.

Each script under ``examples/`` is run as a real subprocess, exactly as
a user would run it. A script that crashes, prints an error, or drifts
away from the current public API fails the suite. The companion
``test_docs_accuracy.py`` checks the *claims* in the docs; this module
proves the shipped code actually *runs*.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"

# The example scripts live at the real repo root, not in mutmut's
# ``mutants/`` sandbox copy; skip there cleanly (out of scope for
# mutation testing of loader logic).
pytestmark = pytest.mark.skipif(
    not EXAMPLES_DIR.exists(),
    reason="examples absent (mutmut sandbox): example checks not applicable",
)


def _run(*command: str, timeout: int = 120) -> str:
    """Run a command from the repo root and assert a clean exit.

    Args:
        command: The argv of the subprocess to launch.
        timeout: Seconds to wait before killing the subprocess.

    Returns:
        The captured standard output of the subprocess.
    """
    env = os.environ.copy()
    env["PATH"] = (
        str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    )
    proc = subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    assert proc.returncode == 0, (
        f"{' '.join(command)} exited {proc.returncode}\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )
    return proc.stdout


def _run_example(script: Path) -> str:
    """Run one example script with the active interpreter.

    Args:
        script: Path to the ``examples/*.py`` script to run.

    Returns:
        The captured standard output of the script.
    """
    return _run(sys.executable, str(script))


def _example_scripts() -> list[Path]:
    """Return every runnable ``examples/*.py`` script, sorted.

    Returns:
        A sorted list of example script paths (``__pycache__`` excluded).
    """
    return sorted(
        py for py in EXAMPLES_DIR.glob("*.py") if "__pycache__" not in str(py)
    )


def test_examples_directory_has_scripts() -> None:
    """The examples directory ships at least one runnable script."""
    assert _example_scripts(), "examples/ has no runnable *.py scripts"


def test_every_example_runs_clean() -> None:
    """Every ``examples/*.py`` script runs as a subprocess and exits 0."""
    for script in _example_scripts():
        _run_example(script)


def test_load_example_lists_transactions() -> None:
    """``01_load_mt942.py`` parses the demo MT942 into two transactions."""
    out = _run_example(EXAMPLES_DIR / "01_load_mt942.py")
    assert "parsed 2 transaction(s):" in out
    assert "500.00" in out
    assert "-200.50" in out


def test_summarize_example_prints_every_summary_field() -> None:
    """``02_summarize_mt942.py`` prints all Mt942Summary roll-up fields."""
    out = _run_example(EXAMPLES_DIR / "02_summarize_mt942.py")
    for label in (
        "reference",
        "account_id",
        "currency",
        "statement_datetime",
        "debit  count/sum",
        "credit count/sum",
        "transaction_count",
        "net of all lines",
    ):
        assert label in out, f"summary example missing {label!r}"
