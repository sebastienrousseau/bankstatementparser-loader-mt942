# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Example: read an MT942 file and print its header-level summary.

Writes a demo MT942 to a temporary file, then loads it with
``load_mt942_file`` and prints the ``Mt942Summary`` roll-ups.

Run with ``python examples/02_summarize_mt942.py``.
"""

import tempfile
from decimal import Decimal
from pathlib import Path

from bankstatementparser_loader_mt942 import (
    load_mt942_file,
    summarize_mt942,
)

MT942 = """:20:MT942-DEMO-2
:25:DE89370400440532013000
:28C:99/2
:34F:EURC0,00
:13D:2506241830+0000
:61:2506240624C1200,00NTRFSALARY//PAYROLL
:86:Salary payment June
:61:2506240624D45,90NTRFGROCERIES//CARD-001
:86:Supermarket card purchase
:61:2506240624D9,99NTRFSTREAM//CARD-002
:86:Streaming subscription
:90D:2EUR55,89
:90C:1EUR1200,00
-
"""


def main() -> None:
    """Write the demo MT942 to disk, load it, and print a summary."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "interim.mt942"
        path.write_text(MT942, encoding="utf-8")

        transactions = load_mt942_file(path)
        summary = summarize_mt942(MT942)

        print(f"reference         : {summary.reference}")
        print(f"account_id        : {summary.account_id}")
        print(f"currency          : {summary.currency}")
        print(f"statement_datetime: {summary.statement_datetime}")
        print(
            f"debit  count/sum  : {summary.debit_count} / {summary.debit_sum}"
        )
        print(
            f"credit count/sum  : "
            f"{summary.credit_count} / {summary.credit_sum}"
        )
        print(f"transaction_count : {summary.transaction_count}")
        net = sum((txn.amount for txn in transactions), start=Decimal(0))
        print(f"net of all lines  : {net}")


if __name__ == "__main__":
    main()
