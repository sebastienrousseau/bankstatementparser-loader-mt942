# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""A malformed SWIFT amount is refused with ``ValueError``.

MT942 amounts are SWIFT ``15d`` comma-decimals: digits, at most one
comma, at most 15 characters. The field regexes accept any run of
digits and commas, so before this was pinned ``1,2,3`` or a bare ``,``
escaped as ``decimal.InvalidOperation`` (not a ``ValueError``, so
callers catching the documented error crashed), and an amount longer
than SWIFT allows was silently rounded to 28 significant digits.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from bankstatementparser_loader_mt942 import load_mt942, summarize_mt942
from bankstatementparser_loader_mt942.loader import _comma_decimal

_PAYLOAD = (
    ":20:REF\n:25:ACC\n:28C:1/1\n:34F:EURC0,00\n"
    ":61:250115D{line}NTRF\n:86:x\n"
    ":90D:{summary}\n:90C:0EUR0,00\n"
)


@pytest.mark.parametrize("amount", ["1,2,3", ",", "1" * 16 + ",00"])
def test_malformed_line_amount_raises_value_error(amount: str) -> None:
    """A bad ``:61:`` amount is a ValueError from both entry points."""
    text = _PAYLOAD.format(line=amount, summary="1EUR1,00")
    with pytest.raises(ValueError, match="SWIFT amount"):
        load_mt942(text)
    with pytest.raises(ValueError, match="SWIFT amount"):
        summarize_mt942(text)


def test_malformed_summary_amount_raises_value_error() -> None:
    """A bad ``:90D:`` amount is a ValueError too."""
    text = _PAYLOAD.format(line="1,00", summary="1EUR1,2,3")
    with pytest.raises(ValueError, match="SWIFT amount"):
        load_mt942(text)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("500,00", Decimal("500.00")),
        ("1,", Decimal("1")),
        ("0,5", Decimal("0.5")),
        ("100", Decimal("100")),
        ("1" * 12 + ",00", Decimal("1" * 12 + ".00")),
    ],
)
def test_well_formed_amounts_still_parse(raw: str, expected: Decimal) -> None:
    """Comma-decimals within SWIFT's 15 characters still convert."""
    assert _comma_decimal(raw) == expected
