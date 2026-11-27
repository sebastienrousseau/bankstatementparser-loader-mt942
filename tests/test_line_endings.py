# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""CRLF and LF payloads load to identical transactions.

The loader documents CRLF/LF differences as tolerated. Before this was
pinned, a multi-line ``:86:`` field kept its ``\\r`` when the file had
CRLF line ends, so a Windows-produced file gave different descriptions
from the same file with LF line ends.
"""

from __future__ import annotations

from bankstatementparser_loader_mt942 import load_mt942

_LF = (
    ":20:REF\n:25:ACC\n:28C:1/1\n:34F:EURC0,00\n"
    ":61:2506240624C1500,00NTRFINV-1//BANK-1\n"
    ":86:Invoice payment\n continued on a second line\n"
    ":90D:0EUR0,00\n:90C:1EUR1500,00\n-"
)


def test_crlf_description_matches_lf() -> None:
    """A CRLF file yields the same descriptions as its LF twin."""
    lf = load_mt942(_LF)
    crlf = load_mt942(_LF.replace("\n", "\r\n"))
    assert [t.description for t in crlf] == [t.description for t in lf]
    assert "\r" not in (crlf[0].description or "")
