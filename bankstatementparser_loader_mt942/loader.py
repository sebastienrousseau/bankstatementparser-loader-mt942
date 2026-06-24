# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""SWIFT MT942 Interim Transaction Report loader.

The core :mod:`bankstatementparser` library parses PDF and CSV bank
statements but does **not** understand the SWIFT MT942 *Interim
Transaction Report* wire format. This module fills that gap: it parses
the MT942 tag grammar and hands back the same
:class:`bankstatementparser.transaction_models.Transaction` objects the
core library produces, so MT942 feeds drop straight into any
downstream consumer (deduplication, categorisation, exports).

MT942 is an *interim* statement: unlike MT940 it carries **no**
``:60F:`` opening or ``:62F:`` closing balance. Instead it reports a
floor limit (``:34F:``), an optional date/time stamp (``:13D:``), the
booked statement lines (``:61:`` / ``:86:``) accumulated so far, and
debit/credit summaries (``:90D:`` / ``:90C:``). This loader models that
structure faithfully and never invents balances that are not present in
the source.

Supported tags:

* ``:20:`` Transaction reference number (mandatory).
* ``:25:`` Account identification (mandatory) — the account id.
* ``:28C:`` Statement / sequence number.
* ``:34F:`` Floor limit indicator ``<CCY>[D|C]<amount>`` — the
  currency for every transaction is taken from here.
* ``:13D:`` Date/time stamp ``YYMMDDHHMM±HHMM`` (optional).
* ``:61:`` Statement line (one per booked entry, repeatable).
* ``:86:`` Information to account owner — attaches its free-form
  description to the immediately preceding ``:61:`` line.
* ``:90D:`` Debit summary ``<count><CCY><amount>``.
* ``:90C:`` Credit summary ``<count><CCY><amount>``.

Amounts use the SWIFT comma decimal separator (``500,00``); they are
converted to :class:`decimal.Decimal` (``Decimal("500.00")``)
throughout. The fractional part is optional: a SWIFT amount may end on
the decimal comma with no digits after it (``5000,`` → ``Decimal("5000")``,
``0,`` → ``Decimal("0")``). Debit lines yield a negative amount, credit
lines a positive amount. Unknown tags and the trailing ``-``
end-of-message marker are tolerated and ignored.

Real-world MT942 messages are frequently wrapped in a **SWIFT message
envelope** — the basic/application/user header blocks ``{1:...}``,
``{2:...}``, ``{3:...}`` and the text-block opener ``{4:`` with a
matching ``-}`` terminator. This loader strips that envelope before
tokenising so the ``:tag:`` body parses cleanly; envelope lines are
never mistaken for content.

Two ``:61:`` constructs that appear in genuine bank exports are handled:

* **Supplementary details after ``:61:``** — a SWIFT statement line may
  carry an optional supplementary-details subfield on the line(s)
  immediately following the ``:61:`` line (before any ``:86:``), e.g. a
  bare ``Transfer`` or ``wording/NBKT``. This loader captures those
  line(s) and folds them into the transaction's ``description`` (they
  are never silently dropped): the description is the supplementary
  text and the following ``:86:`` content joined by newlines, in that
  order.
* **Multi-line ``:86:``** — the ``:86:`` information field continues on
  following lines that do not start with a ``:tag:`` head (e.g.
  ``/BAI/...``, ``/BENM/...``, ``/ACNO/...``). Those continuation lines
  are appended to the ``:86:`` description verbatim, newlines preserved.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from bankstatementparser.transaction_models import Transaction

__all__ = [
    "Mt942Summary",
    "load_mt942",
    "load_mt942_file",
    "summarize_mt942",
]

#: The :class:`~bankstatementparser.transaction_models.Transaction`
#: ``source`` tag stamped on every row this loader produces.
SOURCE = "mt942"


# ─── Regex helpers ───────────────────────────────────────────────────────────

# A field starts with ``:tag:`` at the beginning of a line. Tags are
# 2-3 chars, optionally followed by a single letter (e.g. 28C, 34F).
_FIELD_HEAD_RE = re.compile(r"^:(\d{2}[A-Z]?):", re.MULTILINE)

# A SWIFT envelope header block: ``{1:...}``, ``{2:...}``, ``{3:{...}...}``
# or the text-block opener ``{4:``. The opener has no closing brace on the
# same token (block 4 is terminated later by ``-}``), so it is matched
# separately. Used to strip the envelope before tokenising the body.
_ENVELOPE_BLOCK_RE = re.compile(r"\{[123]:[^{}]*(?:\{[^{}]*\}[^{}]*)*\}")
_BLOCK4_OPEN_RE = re.compile(r"\{4:")
# The block-4 terminator ``-}`` (optionally preceded by whitespace) at the
# very end of the message, e.g. ``...5020,\r\n-}``.
_BLOCK4_CLOSE_RE = re.compile(r"\s*-\}\s*$")

# :34F:EURD500,00  /  :34F:EUR500,00
#       ^CCY ^DC(opt) ^Amount (comma-decimal)
_FLOOR_LIMIT_RE = re.compile(
    r"^(?P<ccy>[A-Z]{3})(?P<dc>[DC])?(?P<amt>[\d,]+)$"
)

# :13D:2506241200+0100
#      ^YYMMDD ^HHMM ^±HHMM
_DATETIME_RE = re.compile(
    r"^(?P<date>\d{6})(?P<time>\d{4})(?P<sign>[+-])(?P<offset>\d{4})$"
)

# :61:2506240624C500,00NTRFREF//BANKREF
#     ^vYYMMDD ^eMMDD(opt) ^DC ^Amt(comma-decimal) ^rest
# Same grammar as MT940 statement lines.
_LINE_RE = re.compile(
    r"^(?P<vdate>\d{6})"
    r"(?P<edate>\d{4})?"
    r"(?P<dc>[CD])"
    r"(?P<amt>[\d,]+)"
    r"(?P<rest>.*)$"
)

# :90D:5EUR1234,56  /  :90C:3EUR987,65
#      ^count ^CCY ^Amount (comma-decimal)
_SUMMARY_RE = re.compile(r"^(?P<count>\d+)(?P<ccy>[A-Z]{3})(?P<amt>[\d,]+)$")


# ─── Summary model ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Mt942Summary:
    """Header-level summary of a parsed MT942 message.

    Captures the metadata and the debit/credit roll-ups that an MT942
    carries in its own right, independent of the individual
    transactions. Every field maps directly to a source tag; nothing is
    derived or invented.

    Attributes:
        reference: The ``:20:`` transaction reference number.
        account_id: The ``:25:`` account identification.
        currency: The currency from the ``:34F:`` floor limit, or
            ``None`` if no floor limit was present.
        statement_datetime: The ``:13D:`` date/time stamp as a
            timezone-aware :class:`datetime.datetime`, or ``None`` when
            the optional tag is absent.
        debit_count: The number of debit entries from ``:90D:``, or
            ``None`` when the tag is absent.
        debit_sum: The summed debit amount from ``:90D:`` as a
            :class:`decimal.Decimal`, or ``None`` when absent.
        credit_count: The number of credit entries from ``:90C:``, or
            ``None`` when the tag is absent.
        credit_sum: The summed credit amount from ``:90C:`` as a
            :class:`decimal.Decimal`, or ``None`` when absent.
        transaction_count: The number of ``:61:`` statement lines
            actually parsed from the message.
    """

    reference: str
    account_id: str
    currency: str | None
    statement_datetime: datetime | None
    debit_count: int | None
    debit_sum: Decimal | None
    credit_count: int | None
    credit_sum: Decimal | None
    transaction_count: int


# ─── Envelope handling ───────────────────────────────────────────────────────


def _strip_envelope(text: str) -> str:
    """Remove a SWIFT message envelope, returning the bare ``:tag:`` body.

    Real-world MT942 messages are commonly wrapped in the SWIFT envelope:
    the header blocks ``{1:...}{2:...}{3:...}`` followed by the text-block
    opener ``{4:`` and a matching ``-}`` terminator at the end::

        {1:F01ASBBNZ2AAXXX000000000001}{2:I942ASBBNZ2AXXXXN}{4:
        :20:...
        ...
        -}

    This strips the leading header blocks and the ``{4:`` opener so the
    ``:tag:`` body tokenises cleanly, and removes a trailing ``-}``
    block-4 terminator. A message with no envelope is returned unchanged,
    so plain ``:tag:`` payloads keep working.

    Args:
        text: The raw MT942 payload, with or without a SWIFT envelope.

    Returns:
        The payload with any SWIFT envelope removed.
    """
    body = text
    open_match = _BLOCK4_OPEN_RE.search(body)
    if open_match is not None:
        # Everything before ``{4:`` is header blocks; the body is what
        # follows the opener. (Header blocks never contain ``:tag:`` lines,
        # so even a malformed header is safely discarded.)
        body = body[open_match.end() :]
        body = _BLOCK4_CLOSE_RE.sub("", body)
    else:
        # No text-block opener: strip any standalone header blocks that may
        # still prefix the body, leaving the bare ``:tag:`` payload.
        body = _ENVELOPE_BLOCK_RE.sub("", body)
    return body


# ─── Tokeniser ──────────────────────────────────────────────────────────────


def _iter_fields(text: str) -> Iterator[tuple[str, str]]:
    """Yield ``(tag, value)`` pairs from an MT942 payload.

    Values may span multiple lines: everything after a ``:tag:`` head
    up to (but not including) the next ``:tag:`` head is the value, with
    the leading tag stripped and surrounding whitespace normalised. The
    trailing ``-`` end-of-message marker and blank lines are absorbed
    into (and stripped from) the preceding value, so they never produce
    a spurious field.

    Args:
        text: The raw MT942 payload.

    Yields:
        ``(tag, value)`` tuples in document order, where ``tag`` is the
        bare tag such as ``"20"`` or ``"34F"``.
    """
    matches = list(_FIELD_HEAD_RE.finditer(text))
    for index, match in enumerate(matches):
        tag = match.group(1)
        value_start = match.end()
        value_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )
        value = text[value_start:value_end].strip()
        # Drop a trailing end-of-message marker on the final field.
        if value.endswith("\n-"):
            value = value[:-2].strip()
        elif value == "-":
            value = ""
        yield tag, value


# ─── Field parsers ──────────────────────────────────────────────────────────


def _comma_decimal(value: str) -> Decimal:
    """Convert a SWIFT comma-decimal amount to a :class:`Decimal`.

    SWIFT uses a comma as the decimal separator (``500,00``); this
    swaps it for a period before constructing the
    :class:`decimal.Decimal` so arithmetic and formatting behave as
    expected.

    Args:
        value: The amount string, e.g. ``"500,00"``.

    Returns:
        The equivalent :class:`decimal.Decimal`, e.g.
        ``Decimal("500.00")``.
    """
    return Decimal(value.replace(",", "."))


def _format_yymmdd(value: str) -> date:
    """Parse a 6-char ``YYMMDD`` date into a :class:`datetime.date`.

    Years are interpreted with a sliding window: ``00``-``79`` map to
    ``20YY`` and ``80``-``99`` to ``19YY``, matching MT940/MT942
    industry practice for any real statement date in the 1980-2079
    range.

    Args:
        value: A 6-character ``YYMMDD`` string.

    Returns:
        The corresponding :class:`datetime.date`.
    """
    year = int(value[0:2])
    century = 2000 if year < 80 else 1900
    return date(century + year, int(value[2:4]), int(value[4:6]))


def _parse_datetime_stamp(value: str) -> datetime | None:
    """Parse a ``:13D:`` ``YYMMDDHHMM±HHMM`` stamp.

    Args:
        value: The ``:13D:`` field value, e.g. ``"2506241200+0100"``.

    Returns:
        A timezone-aware :class:`datetime.datetime`, or ``None`` if the
        value does not match the expected grammar (tolerated rather
        than fatal, since ``:13D:`` is optional).
    """
    match = _DATETIME_RE.match(value)
    if match is None:
        return None
    day = _format_yymmdd(match.group("date"))
    hours = int(match.group("time")[0:2])
    minutes = int(match.group("time")[2:4])
    offset_hours = int(match.group("offset")[0:2])
    offset_minutes = int(match.group("offset")[2:4])
    sign = 1 if match.group("sign") == "+" else -1
    tzinfo = timezone(
        sign * timedelta(hours=offset_hours, minutes=offset_minutes)
    )
    return datetime(
        day.year, day.month, day.day, hours, minutes, tzinfo=tzinfo
    )


def _entry_dates(vdate: str, edate: str | None) -> tuple[date, date | None]:
    """Resolve the value and entry dates from a ``:61:`` line.

    The value date is a full 6-char ``YYMMDD``; the optional entry
    (booking) date is a 4-char ``MMDD`` that inherits its year from the
    value date.

    Args:
        vdate: The 6-character value date (``YYMMDD``).
        edate: The optional 4-character entry date (``MMDD``), or
            ``None``.

    Returns:
        A ``(value_date, booking_date)`` tuple where ``booking_date`` is
        ``None`` when no entry date was present.
    """
    value_date = _format_yymmdd(vdate)
    if edate is None:
        return value_date, None
    booking_date = _format_yymmdd(vdate[0:2] + edate)
    return value_date, booking_date


def _split_reference(rest: str) -> tuple[str | None, str | None]:
    """Split the ``:61:`` tail into a transaction id and a reference.

    The tail of a statement line carries the transaction type
    identification code and reference(s), optionally split on ``//``
    into a bank reference and a customer/account-servicer reference.

    Args:
        rest: The text following the amount on a ``:61:`` line.

    Returns:
        A ``(transaction_id, reference)`` tuple. ``transaction_id`` is
        the bank reference (left of ``//``) and ``reference`` the
        customer reference (right of ``//``); either may be ``None``.
    """
    bank_ref, sep, customer_ref = rest.partition("//")
    transaction_id = bank_ref.strip() or None
    reference = customer_ref.strip() if sep else None
    return transaction_id, (reference or None)


def _parse_summary(value: str, tag: str) -> tuple[int, Decimal]:
    """Parse a ``:90D:`` / ``:90C:`` summary field.

    Args:
        value: The summary field value, e.g. ``"5EUR1234,56"``.
        tag: The originating tag (``"90D"`` or ``"90C"``), used only to
            build a clear error message.

    Returns:
        A ``(count, amount)`` tuple.

    Raises:
        ValueError: If the field does not match the expected
            ``<count><CCY><amount>`` grammar.
    """
    match = _SUMMARY_RE.match(value)
    if match is None:
        raise ValueError(f"Malformed :{tag}: summary field {value!r}")
    return int(match.group("count")), _comma_decimal(match.group("amt"))


# ─── Internal accumulation ───────────────────────────────────────────────────


@dataclass
class _State:
    """Mutable accumulator threaded through the field loop.

    Attributes:
        reference: The ``:20:`` reference, if seen.
        account_id: The ``:25:`` account id, if seen.
        currency: The ``:34F:`` currency, if seen.
        statement_datetime: The ``:13D:`` stamp, if seen.
        debit_count: The ``:90D:`` count, if seen.
        debit_sum: The ``:90D:`` summed amount, if seen.
        credit_count: The ``:90C:`` count, if seen.
        credit_sum: The ``:90C:`` summed amount, if seen.
        records: The accumulated per-transaction field dictionaries.
    """

    reference: str | None = None
    account_id: str | None = None
    currency: str | None = None
    statement_datetime: datetime | None = None
    debit_count: int | None = None
    debit_sum: Decimal | None = None
    credit_count: int | None = None
    credit_sum: Decimal | None = None
    records: list[dict[str, object]] = field(default_factory=list)


def _parse_line(state: _State, value: str) -> None:
    """Parse a ``:61:`` statement line and append it to ``state``.

    A malformed ``:61:`` line is **skipped** (not fatal): the MT942 may
    still carry well-formed lines we want, and a single bad row should
    not abort the whole parse.

    The first physical line is the statement line proper (parsed by the
    ``:61:`` grammar). Any following line(s) are the optional SWIFT
    *supplementary details* subfield — captured separately and folded
    into the transaction's description (see :func:`_fold_description`),
    never glued onto the statement-line tail where they would corrupt the
    reference.

    Args:
        state: The accumulator to append the parsed record to.
        value: The ``:61:`` field value (possibly multi-line).
    """
    first_line, _, supplementary = value.partition("\n")
    match = _LINE_RE.match(first_line)
    if match is None:
        return
    value_date, booking_date = _entry_dates(
        match.group("vdate"), match.group("edate")
    )
    amount = _comma_decimal(match.group("amt"))
    if match.group("dc") == "D":
        amount = -amount
    transaction_id, reference = _split_reference(match.group("rest") or "")
    supplementary_text = supplementary.strip() or None
    state.records.append(
        {
            "amount": amount,
            "value_date": value_date,
            "booking_date": booking_date,
            "transaction_id": transaction_id,
            "reference": reference,
            "supplementary": supplementary_text,
            # Default the description to the supplementary text so a
            # ``:61:`` with supplementary details but no following ``:86:``
            # still carries them; a later ``:86:`` re-folds both together.
            "description": supplementary_text,
        }
    )


def _fold_description(
    supplementary: object, information: str | None
) -> str | None:
    """Combine ``:61:`` supplementary details and ``:86:`` information.

    The transaction description is the ``:61:`` supplementary-details
    text and the ``:86:`` information field joined by a newline, in that
    order. Either may be absent; when both are absent the result is
    ``None``.

    Args:
        supplementary: The ``:61:`` supplementary-details text, or
            ``None``.
        information: The ``:86:`` information text, or ``None``.

    Returns:
        The combined description, or ``None`` when nothing was present.
    """
    parts = [
        part
        for part in (supplementary, information)
        if isinstance(part, str) and part
    ]
    return "\n".join(parts) if parts else None


def _handle_field(state: _State, tag: str, value: str) -> None:
    """Dispatch a single ``(tag, value)`` pair into ``state``.

    Args:
        state: The accumulator to mutate.
        tag: The bare MT942 tag, e.g. ``"20"`` or ``"90D"``.
        value: The field value (already whitespace-stripped).
    """
    if tag == "20":
        state.reference = value or None
    elif tag == "25":
        state.account_id = value or None
    elif tag == "34F":
        match = _FLOOR_LIMIT_RE.match(value)
        if match is not None and state.currency is None:
            state.currency = match.group("ccy")
    elif tag == "13D":
        state.statement_datetime = _parse_datetime_stamp(value)
    elif tag == "61":
        _parse_line(state, value)
    elif tag == "86":
        if state.records:
            record = state.records[-1]
            record["description"] = _fold_description(
                record.get("supplementary"), value or None
            )
    elif tag == "90D":
        state.debit_count, state.debit_sum = _parse_summary(value, "90D")
    elif tag == "90C":
        state.credit_count, state.credit_sum = _parse_summary(value, "90C")
    # :28C: and any unknown tag are ignored (Postel's law).


def _accumulate(text: str) -> _State:
    """Tokenise an MT942 payload and accumulate parsed state.

    Args:
        text: The raw MT942 payload.

    Returns:
        The populated :class:`_State`.

    Raises:
        ValueError: If the mandatory ``:20:`` or ``:25:`` field is
            missing or empty.
    """
    state = _State()
    for tag, value in _iter_fields(_strip_envelope(text)):
        _handle_field(state, tag, value)
    if state.reference is None:
        raise ValueError("MT942 payload missing required :20: reference")
    if state.account_id is None:
        raise ValueError(
            "MT942 payload missing required :25: account identification"
        )
    return state


# ─── Public API ──────────────────────────────────────────────────────────────


def load_mt942(text: str) -> list[Transaction]:
    """Parse an MT942 payload into a list of transactions.

    Each ``:61:`` statement line becomes one
    :class:`~bankstatementparser.transaction_models.Transaction` with
    ``source="mt942"``. Debit lines carry a negative amount, credit
    lines a positive amount. The account id (``:25:``) and currency
    (``:34F:``) are applied to every transaction; the ``:86:``
    description is attached to its preceding ``:61:`` line.

    Args:
        text: The MT942 payload as a string. CRLF/LF differences, blank
            lines, and the trailing ``-`` end-of-message marker are
            tolerated; unknown tags are ignored.

    Returns:
        A list of parsed transactions in document order. Malformed
        ``:61:`` lines are skipped, so the list length may be shorter
        than the number of ``:61:`` tags present.

    Raises:
        ValueError: If the payload is missing the mandatory ``:20:`` or
            ``:25:`` field.
    """
    state = _accumulate(text)
    transactions: list[Transaction] = []
    for index, record in enumerate(state.records):
        enriched: dict[str, object] = dict(record)
        enriched["account_id"] = state.account_id
        enriched["currency"] = state.currency
        transactions.append(
            Transaction.from_record(
                enriched, source=SOURCE, source_index=index
            )
        )
    return transactions


def load_mt942_file(path: str | os.PathLike[str]) -> list[Transaction]:
    """Read an MT942 file from disk and parse it.

    Args:
        path: Filesystem path to a UTF-8 encoded MT942 file.

    Returns:
        A list of parsed transactions, identical to calling
        :func:`load_mt942` on the file's contents.

    Raises:
        ValueError: If the payload is missing the mandatory ``:20:`` or
            ``:25:`` field.
        OSError: If the file cannot be read.
    """
    with open(path, encoding="utf-8") as handle:
        return load_mt942(handle.read())


def summarize_mt942(text: str) -> Mt942Summary:
    """Parse an MT942 payload into a header-level summary.

    Unlike :func:`load_mt942`, this returns the message metadata and the
    ``:90D:`` / ``:90C:`` roll-ups rather than the individual
    transactions, while still counting the ``:61:`` lines that parsed.

    Args:
        text: The MT942 payload as a string.

    Returns:
        An :class:`Mt942Summary` describing the message.

    Raises:
        ValueError: If the payload is missing the mandatory ``:20:`` or
            ``:25:`` field.
    """
    state = _accumulate(text)
    # ``_accumulate`` guarantees these are populated.
    assert state.reference is not None
    assert state.account_id is not None
    return Mt942Summary(
        reference=state.reference,
        account_id=state.account_id,
        currency=state.currency,
        statement_datetime=state.statement_datetime,
        debit_count=state.debit_count,
        debit_sum=state.debit_sum,
        credit_count=state.credit_count,
        credit_sum=state.credit_sum,
        transaction_count=len(state.records),
    )
