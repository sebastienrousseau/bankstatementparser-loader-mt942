# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Golden-style tests over a real-world MT942 corpus.

Each fixture under ``tests/fixtures/`` is a realistic MT942 message that
differs from the others in genuine wire-format detail: ``:61:`` lines
with and without the optional 4-digit entry (booking) date; one versus
two ``:34F:`` floor-limit lines; ``:13D:`` present versus absent; several
mixed credit/debit transactions; and trailing ``-`` end-of-message
markers with stray blank lines.

For every fixture this module pins the **exact** parsed ``Transaction``
list (amount sign and ``Decimal`` value, value and booking dates,
description, ``account_id``, currency, transaction id, reference, source
and source index) and the full nine-field ``Mt942Summary``. A single
parsing regression therefore cannot pass silently: the golden tables
below are the contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from bankstatementparser_loader_mt942 import (
    Mt942Summary,
    load_mt942,
    load_mt942_file,
    summarize_mt942,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@dataclass(frozen=True)
class _ExpectedTxn:
    """The exact parsed shape of one ``Transaction`` in a fixture.

    Attributes:
        source_index: The zero-based index within the message.
        amount: The signed :class:`~decimal.Decimal` amount.
        value_date: The ``:61:`` value date.
        booking_date: The optional entry date, or ``None``.
        description: The ``:86:`` text, or ``None``.
        reference: The resolved customer reference.
        transaction_id: The resolved bank reference / transaction id.
        currency: The ``:34F:`` currency applied to the line.
        account_id: The ``:25:`` account id applied to the line.
    """

    source_index: int
    amount: Decimal
    value_date: date
    booking_date: date | None
    description: str | None
    reference: str | None
    transaction_id: str | None
    currency: str | None
    account_id: str


@dataclass(frozen=True)
class _Case:
    """A fixture file paired with its golden expectations.

    Attributes:
        filename: The fixture basename under ``tests/fixtures/``.
        transactions: The expected ``Transaction`` rows, in order.
        summary: The expected :class:`Mt942Summary`.
    """

    filename: str
    transactions: tuple[_ExpectedTxn, ...]
    summary: Mt942Summary


# Commerzbank EUR: two :34F: floor limits (debit + credit), :13D: present,
# every :61: carries the optional 4-digit entry date, four mixed C/D lines,
# :90D:/:90C: summaries, trailing ``-`` marker.
_COMMERZBANK = _Case(
    filename="commerzbank_eur.mt942",
    transactions=(
        _ExpectedTxn(
            source_index=0,
            amount=Decimal("1500.00"),
            value_date=date(2025, 6, 24),
            booking_date=date(2025, 6, 24),
            description="Salary payment June",
            reference="PAYROLL-06",
            transaction_id="NTRFSALARY",
            currency="EUR",
            account_id="COBADEFFXXX/DE89370400440532013000",
        ),
        _ExpectedTxn(
            source_index=1,
            amount=Decimal("-89.99"),
            value_date=date(2025, 6, 24),
            booking_date=date(2025, 6, 25),
            description="Monthly electricity direct debit",
            reference="ENERGY-INV-771",
            transaction_id="NDDTUTILITY",
            currency="EUR",
            account_id="COBADEFFXXX/DE89370400440532013000",
        ),
        _ExpectedTxn(
            source_index=2,
            amount=Decimal("42.50"),
            value_date=date(2025, 6, 24),
            booking_date=date(2025, 6, 26),
            description="Refund for returned goods",
            reference="SHOP-REFUND",
            transaction_id="NTRFREFUND",
            currency="EUR",
            account_id="COBADEFFXXX/DE89370400440532013000",
        ),
        _ExpectedTxn(
            source_index=3,
            amount=Decimal("-1200.00"),
            value_date=date(2025, 6, 24),
            booking_date=date(2025, 6, 27),
            description="Quarterly office rent",
            reference="LANDLORD-Q3",
            transaction_id="NTRFRENT",
            currency="EUR",
            account_id="COBADEFFXXX/DE89370400440532013000",
        ),
    ),
    summary=Mt942Summary(
        reference="CMZB-942-0001",
        account_id="COBADEFFXXX/DE89370400440532013000",
        currency="EUR",
        statement_datetime=datetime(
            2025, 6, 24, 14, 30, tzinfo=timezone(timedelta(hours=2))
        ),
        debit_count=2,
        debit_sum=Decimal("1289.99"),
        credit_count=2,
        credit_sum=Decimal("1542.50"),
        transaction_count=4,
    ),
)


# Barclays GBP: a single :34F: (credit floor only), no :13D:, every :61:
# WITHOUT the optional entry date (booking_date stays None), stray blank
# lines between fields, one :61: with no ``//`` in its tail, no trailing
# ``-`` marker.
_BARCLAYS = _Case(
    filename="barclays_gbp.mt942",
    transactions=(
        _ExpectedTxn(
            source_index=0,
            amount=Decimal("-250.75"),
            value_date=date(2025, 1, 15),
            booking_date=None,
            description="Card purchase electronics",
            reference="VISA-1234",
            transaction_id="NTRFCARD",
            currency="GBP",
            account_id="BARCGB22/GB29NWBK60161331926819",
        ),
        _ExpectedTxn(
            source_index=1,
            amount=Decimal("3000.00"),
            value_date=date(2025, 1, 15),
            booking_date=None,
            description="Customer invoice settlement",
            reference="ACME-INV-9001",
            transaction_id="NTRFINVOICE",
            currency="GBP",
            account_id="BARCGB22/GB29NWBK60161331926819",
        ),
        _ExpectedTxn(
            source_index=2,
            amount=Decimal("-15.00"),
            value_date=date(2025, 1, 16),
            booking_date=None,
            description="Account maintenance fee",
            # No ``//`` in the tail: the customer reference falls back to
            # the single id (library behaviour), and that id is the
            # transaction_id parsed from the tail.
            reference="NCHGFEE",
            transaction_id="NCHGFEE",
            currency="GBP",
            account_id="BARCGB22/GB29NWBK60161331926819",
        ),
    ),
    summary=Mt942Summary(
        reference="BARC-INTERIM-77",
        account_id="BARCGB22/GB29NWBK60161331926819",
        currency="GBP",
        statement_datetime=None,
        debit_count=2,
        debit_sum=Decimal("265.75"),
        credit_count=1,
        credit_sum=Decimal("3000.00"),
        transaction_count=3,
    ),
)


# Santander USD: a single :34F:, :13D: with a NEGATIVE UTC offset, a mix of
# lines with and without the entry date, one :61: with an empty tail (no
# ids at all), NO :90D:/:90C: summaries (roll-ups default to None), and a
# trailing ``-`` marker preceded by a stray blank line.
#
# The second line exercises the SWIFT MMDD year-inheritance rule at a
# year boundary: a value date of ``241231`` with an entry date of ``0101``
# yields a booking date of ``2024-01-01`` (the entry date inherits the
# value date's ``24`` century-window year verbatim). This is the
# documented behaviour, pinned here on purpose.
_SANTANDER = _Case(
    filename="santander_usd.mt942",
    transactions=(
        _ExpectedTxn(
            source_index=0,
            amount=Decimal("500.00"),
            value_date=date(2024, 12, 31),
            booking_date=None,
            description="Inbound USD wire",
            reference="FX-SETTLE",
            transaction_id="NMSCWIRE-IN",
            currency="USD",
            account_id="BSCHESMMXXX/ES9121000418450200051332",
        ),
        _ExpectedTxn(
            source_index=1,
            amount=Decimal("-75.25"),
            value_date=date(2024, 12, 31),
            booking_date=date(2024, 1, 1),
            description="Brokerage fee",
            reference="BROKER-FEE",
            transaction_id="NTRFFX-FEE",
            currency="USD",
            account_id="BSCHESMMXXX/ES9121000418450200051332",
        ),
        _ExpectedTxn(
            source_index=2,
            amount=Decimal("9.99"),
            value_date=date(2024, 12, 31),
            booking_date=None,
            description="Interest credit",
            reference=None,
            transaction_id=None,
            currency="USD",
            account_id="BSCHESMMXXX/ES9121000418450200051332",
        ),
    ),
    summary=Mt942Summary(
        reference="SANT-USD-INTERIM-03",
        account_id="BSCHESMMXXX/ES9121000418450200051332",
        currency="USD",
        statement_datetime=datetime(
            2024, 12, 31, 23, 59, tzinfo=timezone(timedelta(hours=-5))
        ),
        debit_count=None,
        debit_sum=None,
        credit_count=None,
        credit_sum=None,
        transaction_count=3,
    ),
)


_CASES = (_COMMERZBANK, _BARCLAYS, _SANTANDER)
_CASE_IDS = [case.filename for case in _CASES]


@pytest.fixture(params=_CASES, ids=_CASE_IDS)
def case(request: pytest.FixtureRequest) -> _Case:
    """Yield each corpus case, parametrising the tests below.

    Args:
        request: The pytest request carrying the current ``_Case``.

    Returns:
        The current corpus :class:`_Case`.
    """
    value: _Case = request.param
    return value


def _fixture_text(case: _Case) -> str:
    """Return the raw text of a case's fixture file.

    Args:
        case: The corpus case whose fixture to read.

    Returns:
        The UTF-8 contents of the fixture file.
    """
    return (FIXTURES_DIR / case.filename).read_text(encoding="utf-8")


def test_fixture_files_exist() -> None:
    """Every declared corpus fixture is present on disk."""
    for case in _CASES:
        assert (FIXTURES_DIR / case.filename).is_file()


def test_transaction_count_matches_golden(case: _Case) -> None:
    """The parsed transaction count equals the golden expectation."""
    txns = load_mt942(_fixture_text(case))
    assert len(txns) == len(case.transactions)


def test_each_transaction_matches_golden(case: _Case) -> None:
    """Every field of every parsed transaction matches the golden row."""
    txns = load_mt942(_fixture_text(case))
    for actual, expected in zip(txns, case.transactions, strict=True):
        assert actual.source == "mt942"
        assert actual.source_index == expected.source_index
        assert actual.amount == expected.amount
        # The amount sign is load-bearing: debits negative, credits positive.
        assert (actual.amount < 0) == (expected.amount < 0)
        assert isinstance(actual.amount, Decimal)
        assert actual.value_date == expected.value_date
        assert actual.booking_date == expected.booking_date
        assert actual.description == expected.description
        assert actual.reference == expected.reference
        assert actual.transaction_id == expected.transaction_id
        assert actual.currency == expected.currency
        assert actual.account_id == expected.account_id


def test_summary_matches_golden(case: _Case) -> None:
    """The full nine-field Mt942Summary matches the golden expectation."""
    assert summarize_mt942(_fixture_text(case)) == case.summary


def test_load_mt942_file_matches_load_mt942(case: _Case) -> None:
    """Reading the fixture from disk matches parsing its text in memory."""
    from_file = load_mt942_file(FIXTURES_DIR / case.filename)
    from_text = load_mt942(_fixture_text(case))
    assert [t.amount for t in from_file] == [t.amount for t in from_text]
    assert [t.value_date for t in from_file] == [
        t.value_date for t in from_text
    ]
    assert len(from_file) == len(case.transactions)
