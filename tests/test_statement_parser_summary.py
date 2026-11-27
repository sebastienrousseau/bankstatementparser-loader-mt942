# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""``Mt942StatementParser.get_summary`` fills every field from the file.

These pin the summary dict field by field (and the empty-``:86:``
description), so mutation testing can tell a correct summary from a
plausible-looking wrong one.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from bankstatementparser_loader_mt942 import load_mt942
from bankstatementparser_loader_mt942.loader import Mt942StatementParser


def _write(tmp_path: Path, text: str) -> Path:
    """Write ``text`` as a UTF-8 MT942 file and return its path."""
    path = tmp_path / "statement.mt942"
    path.write_text(text, encoding="utf-8")
    return path


def test_summary_pins_every_field(tmp_path: Path) -> None:
    """Account, last booking date, count, net total and currency."""
    path = _write(
        tmp_path,
        ":20:REF\n:25:ACC1\n:34F:EURC0,00\n"
        ":61:2506240624C500,00NTRFA\n"
        ":61:250625D50,00NTRFB\n"
        ":61:2506260626C25,00NTRFC\n"
        ":90D:1EUR50,00\n:90C:2EUR525,00\n",
    )
    parser = Mt942StatementParser(path)
    summary = parser.get_summary()
    assert summary == {
        "account_id": "ACC1",
        "statement_date": "2025-06-26",
        "transaction_count": 3,
        "total_amount": Decimal("475.00"),
        "opening_balance": None,
        "closing_balance": None,
        "currency": "EUR",
    }
    assert parser.get_summary() is summary


def test_summary_without_rollups_or_entries(tmp_path: Path) -> None:
    """No ``:90x:`` and no ``:61:`` give a zero total and no date."""
    path = _write(tmp_path, ":20:REF\n:25:ACC1\n:34F:GBPC0,00\n")
    assert Mt942StatementParser(path).get_summary() == {
        "account_id": "ACC1",
        "statement_date": None,
        "transaction_count": 0,
        "total_amount": Decimal("0"),
        "opening_balance": None,
        "closing_balance": None,
        "currency": "GBP",
    }


def test_summary_date_skips_nothing_but_the_last_row(tmp_path: Path) -> None:
    """The last row decides the date, even when it has no entry date."""
    path = _write(
        tmp_path,
        ":20:REF\n:25:ACC1\n:34F:EURC0,00\n"
        ":61:2506240624C1,00NTRFA\n"
        ":61:2506250625C1,00NTRFB\n"
        ":61:250626C1,00NTRFC\n"
        ":90C:3EUR3,00\n",
    )
    summary = Mt942StatementParser(path).get_summary()
    assert summary["statement_date"] is None
    assert summary["total_amount"] == Decimal("3.00")


def test_empty_information_leaves_description_none() -> None:
    """An empty ``:86:`` with no supplementary details is no description."""
    text = ":20:REF\n:25:ACC1\n:34F:EURC0,00\n:61:250624C1,00NTRFA\n:86:\n"
    assert load_mt942(text)[0].description is None
