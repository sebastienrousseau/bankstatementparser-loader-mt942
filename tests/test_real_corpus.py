# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Golden test over a *real-world-format* third-party MT942 file.

Unlike the synthetic fixtures in ``test_corpus.py`` (authored for this
project), the file pinned here is vendored byte-for-byte from the
third-party `centrapay/swift-parser <https://github.com/centrapay/swift-parser>`_
test corpus (Apache-2.0). See ``tests/fixtures/real/PROVENANCE.md`` for
provenance and licensing.

It is genuinely messy: it carries a full SWIFT message envelope
(``{1:...}{2:...}{4:`` ... ``-}``), amounts that end on the decimal
comma with no fractional digits (``5000,``, ``0,``), a ``:34F:`` floor
limit with an embedded D/C indicator (``NZDC0,``), multi-line ``:86:``
information fields (``/BAI/`` ... ``/BENM/`` ... ``/ACNO/``), and a
supplementary-details line right after each ``:61:`` (``Transfer`` /
``wording/NBKT``). This test pins the EXACT parsed result, so any
regression in the constructs the loader had to learn fails loudly.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from bankstatementparser_loader_mt942 import (
    Mt942Summary,
    load_mt942_file,
    summarize_mt942,
)

REAL_FILE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "real"
    / "centrapay_swift-parser_test2.mt942"
)

# +1200 (New Zealand) — the offset from the ``:13D:2005211316+1200`` stamp.
_NZST = timezone(timedelta(hours=12))

_ACCOUNT_ID = "123011050612305"

#: The exact transactions the real file must parse into, in order.
_EXPECTED = (
    {
        "source_index": 0,
        "amount": Decimal("-5000"),
        "value_date": date(2020, 5, 21),
        "booking_date": date(2020, 5, 21),
        "currency": "NZD",
        "transaction_id": "NTRFNONREF",
        "reference": "NTRFNONREF",
        "description": (
            "Transfer\n" "/BAI/469/MISCELLANEOUS ACH DEBIT\n" "/BENM/Transfer"
        ),
    },
    {
        "source_index": 1,
        "amount": Decimal("-20"),
        "value_date": date(2020, 5, 21),
        "booking_date": date(2020, 5, 21),
        "currency": "NZD",
        "transaction_id": "NTRFNONREF",
        "reference": "NTRFNONREF",
        "description": (
            "Transfer\n"
            "/BAI/469/MISCELLANEOUS ACH DEBIT\n"
            "/BENM/Transfer\n"
            "/ACNO/012-3011-00334130-0037"
        ),
    },
    {
        "source_index": 2,
        "amount": Decimal("5020"),
        "value_date": date(2020, 5, 21),
        "booking_date": date(2020, 5, 21),
        "currency": "NZD",
        "transaction_id": "NBKTNONREF",
        "reference": "NBKTNONREF",
        "description": (
            "wording/NBKT\n"
            "/BAI/399/MISCELLANEOUS CREDIT\n"
            "/ORDP/wording\n"
            "/ACNO/12-3011-0334130-37"
        ),
    },
)

_EXPECTED_SUMMARY = Mt942Summary(
    reference="FNB5014200018001",
    account_id=_ACCOUNT_ID,
    currency="NZD",
    statement_datetime=datetime(2020, 5, 21, 13, 16, tzinfo=_NZST),
    debit_count=2,
    debit_sum=Decimal("5020"),
    credit_count=1,
    credit_sum=Decimal("5020"),
    transaction_count=3,
)


def test_real_file_is_present() -> None:
    """The vendored third-party fixture exists on disk."""
    assert REAL_FILE.is_file()


def test_real_file_parses_to_three_transactions() -> None:
    """The real file yields exactly three transactions."""
    assert len(load_mt942_file(REAL_FILE)) == 3


def test_real_file_transactions_match_golden() -> None:
    """Every field of every parsed real-file transaction is pinned.

    This is the proof the messy real-world constructs (envelope,
    trailing-comma amounts, multi-line ``:86:``, ``:61:`` supplementary
    line) parse correctly.
    """
    txns = load_mt942_file(REAL_FILE)
    for actual, expected in zip(txns, _EXPECTED, strict=True):
        assert actual.source == "mt942"
        assert actual.source_index == expected["source_index"]
        assert actual.amount == expected["amount"]
        assert isinstance(actual.amount, Decimal)
        assert (actual.amount < 0) == (expected["amount"] < 0)
        assert actual.value_date == expected["value_date"]
        assert actual.booking_date == expected["booking_date"]
        assert actual.currency == expected["currency"]
        assert actual.account_id == _ACCOUNT_ID
        assert actual.transaction_id == expected["transaction_id"]
        assert actual.reference == expected["reference"]
        assert actual.description == expected["description"]


def test_real_file_summary_matches_golden() -> None:
    """The full nine-field summary of the real file is pinned."""
    summary = summarize_mt942(REAL_FILE.read_text(encoding="utf-8"))
    assert summary == _EXPECTED_SUMMARY
