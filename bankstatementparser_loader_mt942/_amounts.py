# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""SWIFT ``15d`` comma-decimal amounts to ``Decimal``."""

from __future__ import annotations

import re
from decimal import Decimal

# SWIFT ``15d``: ASCII digits with at most one comma as the decimal
# separator, at most 15 characters in all. The field regexes accept any
# run of digits and commas, so ``1,2,3`` or a lone ``,`` reach here.
_AMOUNT_RE = re.compile(r"[0-9]+(?:,[0-9]*)?")
_MAX_LENGTH = 15


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

    Raises:
        ValueError: If ``value`` is not digits with at most one comma,
            or is longer than the 15 characters SWIFT allows (longer
            amounts would be rounded by ``Decimal`` arithmetic).
    """
    if len(value) > _MAX_LENGTH or _AMOUNT_RE.fullmatch(value) is None:
        raise ValueError(f"SWIFT amount {value!r} is not a 15d comma-decimal")
    return Decimal(value.replace(",", "."))
