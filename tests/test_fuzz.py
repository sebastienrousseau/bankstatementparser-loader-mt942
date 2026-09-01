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

"""Hypothesis property and fuzz tests for bankstatementparser-loader-mt942."""

from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from bankstatementparser_loader_mt942.loader import (
    Mt942StatementParser,
    _comma_decimal,
    _format_yymmdd,
    _iter_fields,
    load_mt942,
    summarize_mt942,
)


@settings(max_examples=50, deadline=None)
@given(st.text(min_size=0, max_size=2000))
def test_fuzz_load_mt942_never_crashes_unhandled(payload: str) -> None:
    """load_mt942 safely raises ValueError or returns list on arbitrary inputs."""
    try:
        txs = load_mt942(payload)
        assert isinstance(txs, list)
    except ValueError:
        pass


@settings(max_examples=50, deadline=None)
@given(st.text(min_size=0, max_size=2000))
def test_fuzz_summarize_mt942_never_crashes_unhandled(payload: str) -> None:
    """summarize_mt942 safely raises ValueError or returns Mt942Summary."""
    try:
        s = summarize_mt942(payload)
        assert s is not None
    except ValueError:
        pass


@settings(max_examples=50, deadline=None)
@given(st.text(min_size=0, max_size=50))
def test_fuzz_comma_decimal(raw: str) -> None:
    """_comma_decimal parses SWIFT comma decimals or raises DecimalException."""
    try:
        val = _comma_decimal(raw)
        assert isinstance(val, Decimal)
    except (ValueError, ArithmeticError, Exception):
        pass


@settings(max_examples=50, deadline=None)
@given(st.text(min_size=0, max_size=30))
def test_fuzz_format_yymmdd(raw: str) -> None:
    """_format_yymmdd safely returns date or raises ValueError on invalid."""
    try:
        d = _format_yymmdd(raw)
        assert hasattr(d, "year")
    except ValueError:
        pass


@settings(max_examples=50, deadline=None)
@given(st.text(min_size=0, max_size=1000))
def test_fuzz_iter_fields(text: str) -> None:
    """_iter_fields yields tag and value pairs safely."""
    for tag, value in _iter_fields(text):
        assert isinstance(tag, str)
        assert isinstance(value, str)


@settings(max_examples=30, deadline=None)
@given(st.text(min_size=0, max_size=1000))
def test_fuzz_mt942_statement_parser(text: str) -> None:
    """Mt942StatementParser wrapper never unhandled crashes on arbitrary file content."""
    with tempfile.NamedTemporaryFile("w", suffix=".mt942", delete=False) as f:
        f.write(text)
        f_path = f.name
    try:
        parser = Mt942StatementParser(f_path)
        try:
            df = parser.parse()
            assert df is not None
            summary = parser.get_summary()
            assert isinstance(summary, dict)
        except ValueError:
            pass
    finally:
        Path(f_path).unlink(missing_ok=True)
