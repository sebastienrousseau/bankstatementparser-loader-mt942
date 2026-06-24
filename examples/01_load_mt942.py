# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Minimal example: parse a tiny MT942 payload into transactions.

Run with ``python examples/01_load_mt942.py``.
"""

from bankstatementparser_loader_mt942 import load_mt942

MT942 = """:20:MT942-DEMO-1
:25:COBADEFFXXX/DE89370400440532013000
:28C:42/1
:34F:EURD0,00
:34F:EURC0,00
:13D:2506241200+0100
:61:2506240624C500,00NTRFINV-123//BANKREF1
:86:Incoming payment for invoice 123
:61:2506240624D200,50NTRFRENT//BANKREF2
:86:Monthly rent debit
:90D:1EUR200,50
:90C:1EUR500,00
-
"""


def main() -> None:
    """Parse the demo MT942 and print one line per transaction."""
    transactions = load_mt942(MT942)
    print(f"parsed {len(transactions)} transaction(s):")
    for txn in transactions:
        print(
            f"  [{txn.source_index}] {txn.value_date} "
            f"{txn.currency} {txn.amount:>9} "
            f"{txn.description!r} (id={txn.transaction_id})"
        )


if __name__ == "__main__":
    main()
