# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Every SWIFT debit/credit mark on a ``:61:`` line is loaded and signed.

Field 61's mark is ``C``, ``D``, ``RC`` (reversal of a credit, so a
debit), ``RD`` (reversal of a debit, so a credit) or, in MT942, ``EC`` /
``ED`` (expected credit / debit), optionally followed by a one-letter
funds code. Before this was pinned only a bare ``C`` or ``D`` matched,
so reversals, expected entries and any line with a funds code were
dropped as malformed without a word.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from bankstatementparser_loader_mt942 import load_mt942, summarize_mt942

_PAYLOAD = ":20:REF\n:25:ACC\n:34F:EURC0,00\n:61:250624{mark}100,00NTRFX\n"


@pytest.mark.parametrize(
    ("mark", "amount"),
    [
        ("C", Decimal("100.00")),
        ("D", Decimal("-100.00")),
        ("RC", Decimal("-100.00")),
        ("RD", Decimal("100.00")),
        ("EC", Decimal("100.00")),
        ("ED", Decimal("-100.00")),
        ("DR", Decimal("-100.00")),
        ("CX", Decimal("100.00")),
        ("RDX", Decimal("100.00")),
    ],
)
def test_mark_is_loaded_with_its_sign(mark: str, amount: Decimal) -> None:
    """Each mark (and an optional funds code) yields one signed entry."""
    text = _PAYLOAD.format(mark=mark)
    assert [t.amount for t in load_mt942(text)] == [amount]
    assert summarize_mt942(text).transaction_count == 1
