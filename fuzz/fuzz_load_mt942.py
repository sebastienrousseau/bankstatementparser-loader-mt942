# Copyright (C) 2023-2026 Bank Statement Parser. All rights reserved.
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

"""Coverage-guided Atheris fuzz target for the MT942 loader.

``load_mt942`` and ``summarize_mt942`` are the package's two entry
points for untrusted text, and they promise one failure mode for bad
input: ``ValueError`` (a missing ``:20:`` or ``:25:``, a malformed
summary or amount, an impossible date). Any other exception escapes
the target and libFuzzer records it as a crash. Every transaction that
does load must also be well formed: a finite amount and
``source == "mt942"``; and when the load succeeds, the summary must
too, counting the same transactions.

Run (Linux x86_64, Python 3.12+, ``poetry install --with fuzz``)::

    python fuzz/fuzz_load_mt942.py fuzz/corpus -max_total_time=60
"""

from __future__ import annotations

import sys

import atheris

with atheris.instrument_imports():
    from bankstatementparser_loader_mt942 import load_mt942, summarize_mt942


def test_one_input(data: bytes) -> None:
    """Load and summarise one fuzz input as MT942 text."""
    text = atheris.FuzzedDataProvider(data).ConsumeUnicodeNoSurrogates(
        len(data)
    )
    try:
        transactions = load_mt942(text)
    except ValueError:
        return
    for txn in transactions:
        if not txn.amount.is_finite() or txn.source != "mt942":
            raise AssertionError(f"malformed transaction {txn!r}")
    summary = summarize_mt942(text)
    if summary.transaction_count != len(transactions):
        raise AssertionError(
            f"summary counts {summary.transaction_count}, "
            f"load returned {len(transactions)}"
        )


def main() -> None:
    """Hand the target to libFuzzer with the command-line options."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
