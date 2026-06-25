# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Tests for the bankstatementparser-loader-mt942 loader."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from bankstatementparser_loader_mt942 import (
    Mt942Summary,
    __version__,
    load_mt942,
    load_mt942_file,
    summarize_mt942,
)


def _full_mt942() -> str:
    """Return a realistic MT942 covering every supported tag.

    Includes :20:, :25:, :28C:, two :34F: floor limits, :13D:, two
    :61:+:86: lines (one credit, one debit), :90D:, :90C:, and the
    trailing ``-`` end-of-message marker.
    """
    return (
        ":20:MT942REF001\n"
        ":25:COBADEFFXXX/DE89370400440532013000\n"
        ":28C:42/1\n"
        ":34F:EURD0,00\n"
        ":34F:EURC0,00\n"
        ":13D:2506241200+0100\n"
        ":61:2506240624C500,00NTRFINV-123//BANKREF1\n"
        ":86:Incoming payment for invoice 123\n"
        ":61:2506240624D200,50NTRFRENT//BANKREF2\n"
        ":86:Monthly rent debit\n"
        ":90D:1EUR200,50\n"
        ":90C:1EUR500,00\n"
        "-\n"
    )


def test_version_exposed() -> None:
    """The package exposes a non-empty semantic-style version string."""
    assert isinstance(__version__, str)
    assert __version__.count(".") >= 2


def test_full_message_yields_two_transactions() -> None:
    """The realistic sample parses into exactly two transactions."""
    txns = load_mt942(_full_mt942())
    assert len(txns) == 2
    assert [t.source for t in txns] == ["mt942", "mt942"]
    assert [t.source_index for t in txns] == [0, 1]


def test_credit_line_is_positive_with_decimal_amount() -> None:
    """A credit :61: line yields a positive Decimal amount."""
    credit = load_mt942(_full_mt942())[0]
    assert credit.amount == Decimal("500.00")
    assert credit.amount > 0


def test_debit_line_is_negative_with_decimal_amount() -> None:
    """A debit :61: line yields a negative Decimal amount."""
    debit = load_mt942(_full_mt942())[1]
    assert debit.amount == Decimal("-200.50")
    assert debit.amount < 0


def test_account_id_and_currency_applied_to_every_transaction() -> None:
    """:25: account id and :34F: currency reach every transaction."""
    txns = load_mt942(_full_mt942())
    for txn in txns:
        assert txn.account_id == "COBADEFFXXX/DE89370400440532013000"
        assert txn.currency == "EUR"


def test_description_attaches_from_following_tag_86() -> None:
    """:86: free-form text attaches to its preceding :61: line."""
    txns = load_mt942(_full_mt942())
    assert txns[0].description == "Incoming payment for invoice 123"
    assert txns[1].description == "Monthly rent debit"


def test_references_split_on_double_slash() -> None:
    """The :61: tail splits into transaction_id and reference on ``//``."""
    credit = load_mt942(_full_mt942())[0]
    assert credit.transaction_id == "NTRFINV-123"
    assert credit.reference == "BANKREF1"


def test_value_date_parsed_from_statement_line() -> None:
    """The :61: value date is parsed into a date object."""
    credit = load_mt942(_full_mt942())[0]
    assert credit.value_date == date(2025, 6, 24)


def test_entry_date_inherits_year_for_booking_date() -> None:
    """The 4-char entry date inherits its year for booking_date."""
    credit = load_mt942(_full_mt942())[0]
    assert credit.booking_date == date(2025, 6, 24)


def test_summary_reports_metadata_and_rollups() -> None:
    """summarize_mt942 returns the header metadata and :90x: roll-ups."""
    summary = summarize_mt942(_full_mt942())
    assert isinstance(summary, Mt942Summary)
    assert summary.reference == "MT942REF001"
    assert summary.account_id == "COBADEFFXXX/DE89370400440532013000"
    assert summary.currency == "EUR"
    assert summary.debit_count == 1
    assert summary.debit_sum == Decimal("200.50")
    assert summary.credit_count == 1
    assert summary.credit_sum == Decimal("500.00")
    assert summary.transaction_count == 2


def test_summary_datetime_is_timezone_aware() -> None:
    """The :13D: stamp parses into a timezone-aware datetime."""
    summary = summarize_mt942(_full_mt942())
    expected = datetime(
        2025, 6, 24, 12, 0, tzinfo=timezone(timedelta(hours=1))
    )
    assert summary.statement_datetime == expected


def test_negative_offset_datetime_stamp() -> None:
    """A :13D: stamp with a negative UTC offset parses correctly."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":13D:2506240800-0530\n"
    summary = summarize_mt942(mt942)
    assert summary.statement_datetime == datetime(
        2025, 6, 24, 8, 0, tzinfo=timezone(timedelta(hours=-5, minutes=-30))
    )


def test_floor_limit_without_dc_indicator_captures_currency() -> None:
    """A :34F: floor limit with no D/C indicator still yields currency."""
    mt942 = (
        ":20:REF\n" ":25:ACC\n" ":34F:USD1000,00\n" ":61:250624C10,00NTRFX\n"
    )
    txns = load_mt942(mt942)
    assert txns[0].currency == "USD"


def test_first_floor_limit_wins_for_currency() -> None:
    """When two :34F: lines disagree, the first currency is kept."""
    mt942 = (
        ":20:REF\n"
        ":25:ACC\n"
        ":34F:EURD0,00\n"
        ":34F:GBPC0,00\n"
        ":61:250624C10,00NTRFX\n"
    )
    assert load_mt942(mt942)[0].currency == "EUR"


def test_currency_none_when_no_floor_limit() -> None:
    """Without a :34F: tag the currency is None."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":61:250624C10,00NTRFX\n"
    assert load_mt942(mt942)[0].currency is None
    assert summarize_mt942(mt942).currency is None


def test_statement_line_without_entry_date_leaves_booking_none() -> None:
    """A :61: line with only a value date leaves booking_date None."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":34F:EURC0,00\n" ":61:250624C10,00NTRFX\n"
    txn = load_mt942(mt942)[0]
    assert txn.value_date == date(2025, 6, 24)
    assert txn.booking_date is None


def test_line_without_double_slash_keeps_only_transaction_id() -> None:
    """A :61: tail with no ``//`` yields a transaction_id and no customer ref.

    The loader supplies no explicit customer ``reference`` (there is no
    ``//`` split), so the core ``Transaction.from_record`` mapping falls
    back to the transaction id for the ``reference`` field. That fallback
    is library behaviour, not loader behaviour; the loader's contribution
    is the single id parsed from the tail.
    """
    mt942 = (
        ":20:REF\n"
        ":25:ACC\n"
        ":34F:EURC0,00\n"
        ":61:250624C10,00NTRFONLYID\n"
    )
    txn = load_mt942(mt942)[0]
    assert txn.transaction_id == "NTRFONLYID"
    assert txn.reference == "NTRFONLYID"


def test_line_with_empty_tail_has_no_ids() -> None:
    """A :61: line with no trailing text yields no ids or reference."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":34F:EURC0,00\n" ":61:250624C10,00\n"
    txn = load_mt942(mt942)[0]
    assert txn.transaction_id is None
    assert txn.reference is None


def test_missing_description_leaves_description_none() -> None:
    """A :61: line with no following :86: keeps description None."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":34F:EURC0,00\n" ":61:250624C10,00NTRFX\n"
    assert load_mt942(mt942)[0].description is None


def test_orphan_tag_86_before_any_line_is_ignored() -> None:
    """An :86: with no preceding :61: is silently dropped."""
    mt942 = (
        ":20:REF\n"
        ":25:ACC\n"
        ":34F:EURC0,00\n"
        ":86:Orphan info with no entry\n"
        ":61:250624C10,00NTRFX\n"
    )
    txns = load_mt942(mt942)
    assert len(txns) == 1
    assert txns[0].description is None


def test_malformed_statement_line_is_skipped() -> None:
    """A :61: line that does not match the grammar is skipped, not fatal."""
    mt942 = (
        ":20:REF\n"
        ":25:ACC\n"
        ":34F:EURC0,00\n"
        ":61:NOT-A-VALID-LINE\n"
        ":61:250624C10,00NTRFGOOD\n"
    )
    txns = load_mt942(mt942)
    assert len(txns) == 1
    assert txns[0].transaction_id == "NTRFGOOD"


def test_malformed_datetime_stamp_yields_none() -> None:
    """A :13D: that does not match the grammar leaves the datetime None."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":13D:GARBAGE\n"
    assert summarize_mt942(mt942).statement_datetime is None


def test_unknown_tags_are_ignored() -> None:
    """Unknown tags (e.g. :28C:, :86: trailers) never break parsing."""
    mt942 = (
        ":20:REF\n"
        ":21:RELATED-REF\n"
        ":25:ACC\n"
        ":28C:99/2\n"
        ":34F:EURC0,00\n"
        ":61:250624C10,00NTRFX\n"
    )
    txns = load_mt942(mt942)
    assert len(txns) == 1


def test_trailing_dash_marker_does_not_create_a_field() -> None:
    """A trailing ``-`` end-of-message marker is absorbed, not parsed."""
    mt942 = (
        ":20:REF\n"
        ":25:ACC\n"
        ":34F:EURC0,00\n"
        ":61:250624C10,00NTRFX\n"
        "-\n"
    )
    txns = load_mt942(mt942)
    assert len(txns) == 1
    assert txns[0].transaction_id == "NTRFX"


def test_lone_dash_field_value_is_emptied() -> None:
    """A field whose entire value is ``-`` is treated as empty.

    The loader normalises a bare ``-`` marker to an empty string; the
    core ``Transaction.from_record`` then treats an empty description as
    absent and leaves ``description`` as ``None``.
    """
    mt942 = (
        ":20:REF\n"
        ":25:ACC\n"
        ":34F:EURC0,00\n"
        ":61:250624C10,00NTRFX\n"
        ":86:-"
    )
    txns = load_mt942(mt942)
    assert txns[0].description is None


def test_blank_lines_are_tolerated() -> None:
    """Blank lines between fields do not affect parsing."""
    mt942 = (
        ":20:REF\n"
        "\n"
        ":25:ACC\n"
        "\n"
        ":34F:EURC0,00\n"
        "\n"
        ":61:250624C10,00NTRFX\n"
    )
    assert len(load_mt942(mt942)) == 1


def test_missing_tag_20_raises() -> None:
    """A payload without :20: raises ValueError mentioning the tag."""
    mt942 = ":25:ACC\n" ":34F:EURC0,00\n" ":61:250624C10,00NTRFX\n"
    with pytest.raises(ValueError, match=":20:"):
        load_mt942(mt942)


def test_empty_tag_20_raises() -> None:
    """A payload with an empty :20: value is treated as missing."""
    mt942 = ":20:\n" ":25:ACC\n" ":34F:EURC0,00\n"
    with pytest.raises(ValueError, match=":20:"):
        load_mt942(mt942)


def test_missing_tag_25_raises() -> None:
    """A payload without :25: raises ValueError mentioning the tag."""
    mt942 = ":20:REF\n" ":34F:EURC0,00\n" ":61:250624C10,00NTRFX\n"
    with pytest.raises(ValueError, match=":25:"):
        load_mt942(mt942)


def test_empty_tag_25_raises() -> None:
    """A payload with an empty :25: value is treated as missing."""
    mt942 = ":20:REF\n" ":25:\n" ":34F:EURC0,00\n"
    with pytest.raises(ValueError, match=":25:"):
        load_mt942(mt942)


def test_malformed_debit_summary_raises() -> None:
    """A malformed :90D: summary raises ValueError mentioning the tag."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":34F:EURC0,00\n" ":90D:JUNK\n"
    with pytest.raises(ValueError, match="90D"):
        summarize_mt942(mt942)


def test_malformed_credit_summary_raises() -> None:
    """A malformed :90C: summary raises ValueError mentioning the tag."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":34F:EURC0,00\n" ":90C:NOPE\n"
    with pytest.raises(ValueError, match="90C"):
        summarize_mt942(mt942)


def test_summary_counts_only_well_formed_lines() -> None:
    """transaction_count reflects only the :61: lines that parsed."""
    mt942 = (
        ":20:REF\n"
        ":25:ACC\n"
        ":34F:EURC0,00\n"
        ":61:BADLINE\n"
        ":61:250624C10,00NTRFX\n"
    )
    assert summarize_mt942(mt942).transaction_count == 1


def test_summary_optional_rollups_default_to_none() -> None:
    """Without :90D:/:90C:/:13D: the summary fields default to None."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":34F:EURC0,00\n" ":61:250624C10,00NTRFX\n"
    summary = summarize_mt942(mt942)
    assert summary.debit_count is None
    assert summary.debit_sum is None
    assert summary.credit_count is None
    assert summary.credit_sum is None
    assert summary.statement_datetime is None


def test_old_date_uses_19xx_window() -> None:
    """A value date with YY >= 80 maps into the 1900s window."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":34F:EURC0,00\n" ":61:950624C10,00NTRFX\n"
    assert load_mt942(mt942)[0].value_date == date(1995, 6, 24)


def test_message_with_no_statement_lines_yields_empty_list() -> None:
    """A valid header with no :61: lines parses to an empty list."""
    mt942 = ":20:REF\n" ":25:ACC\n" ":34F:EURC0,00\n"
    assert load_mt942(mt942) == []
    assert summarize_mt942(mt942).transaction_count == 0


def test_load_mt942_file_round_trip(tmp_path) -> None:
    """load_mt942_file reads from disk and parses identically."""
    path = tmp_path / "statement.mt942"
    path.write_text(_full_mt942(), encoding="utf-8")
    from_file = load_mt942_file(path)
    from_string = load_mt942(_full_mt942())
    assert [t.amount for t in from_file] == [t.amount for t in from_string]
    assert len(from_file) == 2


def test_load_mt942_file_accepts_str_path(tmp_path) -> None:
    """load_mt942_file accepts a plain string path as well as PathLike."""
    path = tmp_path / "statement.mt942"
    path.write_text(_full_mt942(), encoding="utf-8")
    txns = load_mt942_file(str(path))
    assert len(txns) == 2


# ─── Real-world constructs (v0.0.13) ─────────────────────────────────────────


def test_swift_envelope_with_block4_is_stripped() -> None:
    """A full SWIFT envelope (``{1:}{2:}{4:`` ... ``-}``) is stripped.

    The header blocks and the block-4 opener/terminator must not be
    parsed as content; only the ``:tag:`` body survives.
    """
    mt942 = (
        "{1:F01BANKXXXX0000000000}{2:I942BANKXXXXN}{4:\r\n"
        ":20:REF\r\n"
        ":25:ACC\r\n"
        ":34F:EURC0,00\r\n"
        ":61:250624C10,00NTRFGOOD\r\n"
        "-}"
    )
    txns = load_mt942(mt942)
    assert len(txns) == 1
    assert txns[0].transaction_id == "NTRFGOOD"


def test_standalone_header_block_without_block4_is_stripped() -> None:
    """A header block with no ``{4:`` opener is still stripped.

    Exercises the no-text-block-opener branch of envelope stripping: a
    ``{3:{...}}`` user-header block prefixing the body must be removed so
    the following ``:20:`` is recognised at line start.
    """
    mt942 = (
        "{3:{108:MYREF}}:20:REF\n"
        ":25:ACC\n"
        ":34F:EURC0,00\n"
        ":61:250624C10,00NTRFGOOD\n"
    )
    txns = load_mt942(mt942)
    assert len(txns) == 1
    assert txns[0].transaction_id == "NTRFGOOD"


def test_amount_with_trailing_comma_no_decimals() -> None:
    """A SWIFT amount ending on the decimal comma parses with no digits.

    ``5000,`` must become ``Decimal("5000")`` (not raise, not ``5000.0``
    with spurious precision).
    """
    debit = load_mt942(
        ":20:REF\n:25:ACC\n:34F:NZDC0,\n:61:200521D5000,NTRFNONREF\n"
    )[0]
    assert debit.amount == Decimal("-5000")
    assert debit.amount == Decimal("-5000.00")


def test_floor_limit_with_embedded_dc_indicator_parses_currency() -> None:
    """``:34F:NZDC0,`` yields currency NZD regardless of the C indicator."""
    txn = load_mt942(":20:REF\n:25:ACC\n:34F:NZDC0,\n:61:250624C10,00NTRFX\n")[
        0
    ]
    assert txn.currency == "NZD"


def test_lone_dash_floor_limit_does_not_crash() -> None:
    """A lone-dash ``:34F:-`` value is treated as empty, not ``None``.

    The tokeniser must emit an empty string (not ``None``) for a bare
    ``-`` field so the floor-limit regex receives a string; a ``None``
    would raise ``TypeError`` in ``re.match``.
    """
    txns = load_mt942(":20:REF\n:25:ACC\n:34F:-\n:61:250624C10,00NTRFX\n")
    assert txns[0].currency is None


def test_supplementary_line_after_61_without_86_becomes_description() -> None:
    """A ``:61:`` supplementary line with no ``:86:`` is kept as description.

    The supplementary-details subfield is folded into the transaction;
    it must never be dropped, and must never corrupt the reference.
    """
    txn = load_mt942(
        ":20:REF\n"
        ":25:ACC\n"
        ":34F:EURC0,00\n"
        ":61:250624C10,00NTRFGOOD\n"
        "SupplementaryWording\n"
    )[0]
    assert txn.transaction_id == "NTRFGOOD"
    assert txn.description == "SupplementaryWording"


def test_supplementary_line_and_86_are_folded_in_order() -> None:
    """Supplementary text and ``:86:`` join newline-separated, supp first."""
    txn = load_mt942(
        ":20:REF\n"
        ":25:ACC\n"
        ":34F:EURC0,00\n"
        ":61:250624C10,00NTRFGOOD\n"
        "Transfer\n"
        ":86:/BAI/469/INFO\n"
    )[0]
    assert txn.description == "Transfer\n/BAI/469/INFO"


def test_multi_line_86_continuation_is_appended() -> None:
    """``:86:`` continuation lines (no ``:tag:`` head) join the description."""
    txn = load_mt942(
        ":20:REF\n"
        ":25:ACC\n"
        ":34F:EURC0,00\n"
        ":61:250624C10,00NTRFGOOD\n"
        ":86:/BAI/469/INFO\n"
        "/BENM/Transfer\n"
        "/ACNO/12-34\n"
    )[0]
    assert txn.description == "/BAI/469/INFO\n/BENM/Transfer\n/ACNO/12-34"


def test_year_eighty_maps_to_nineteen_eighties() -> None:
    """The SWIFT sliding window: ``YY == 80`` maps to 1980, not 2080."""
    txn = load_mt942(
        ":20:REF\n:25:ACC\n:34F:EURC0,00\n:61:800624C10,00NTRFX\n"
    )[0]
    assert txn.value_date == date(1980, 6, 24)


def test_year_seventy_nine_maps_to_twenty_seventies() -> None:
    """The SWIFT sliding window: ``YY == 79`` maps to 2079."""
    txn = load_mt942(
        ":20:REF\n:25:ACC\n:34F:EURC0,00\n:61:790624C10,00NTRFX\n"
    )[0]
    assert txn.value_date == date(2079, 6, 24)


def test_missing_tag_20_error_message_is_exact() -> None:
    """The ``:20:`` error message text is pinned exactly."""
    with pytest.raises(
        ValueError, match=r"^MT942 payload missing required :20: reference$"
    ):
        load_mt942(":25:ACC\n:34F:EURC0,00\n")


def test_missing_tag_25_error_message_is_exact() -> None:
    """The ``:25:`` error message text is pinned exactly."""
    with pytest.raises(
        ValueError,
        match=(
            r"^MT942 payload missing required :25: account identification$"
        ),
    ):
        load_mt942(":20:REF\n:34F:EURC0,00\n")


def test_malformed_debit_summary_error_names_tag_exactly() -> None:
    """The ``:90D:`` error message uses the exact tag, not a mutated one."""
    with pytest.raises(ValueError, match=r"^Malformed :90D: summary field"):
        summarize_mt942(":20:REF\n:25:ACC\n:90D:JUNK\n")


def test_malformed_credit_summary_error_names_tag_exactly() -> None:
    """The ``:90C:`` error message uses the exact tag, not a mutated one."""
    with pytest.raises(ValueError, match=r"^Malformed :90C: summary field"):
        summarize_mt942(":20:REF\n:25:ACC\n:90C:JUNK\n")
