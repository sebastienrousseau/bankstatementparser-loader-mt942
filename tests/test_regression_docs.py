# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Regression suite: every ```python``` block in the docs must run.

``test_docs_accuracy.py`` checks that the *claims* around the code match
the codebase; this module goes further and *executes* the documented
snippets themselves, in-process:

* Every fenced ``python`` block in README.md (and any ``docs/*.md``) is
  classified in ``BLOCK_SPECS`` below. Adding a new python block to the
  docs without classifying it fails the suite — examples cannot silently
  rot.
* Each classified block is compiled and executed against a fresh
  namespace. Blocks that read a file have that file materialised in a
  per-test temp directory first (via a ``preamble``).
* A block expected to raise is run with ``pytest.raises``.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Markdown files whose python blocks are executed by this suite. Only
#: README.md ships embedded python; ``docs/*.md`` are include shims.
DOC_FILES: tuple[str, ...] = ("README.md",)


# ----------------------------------------------------------------------
# Block extraction
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class DocBlock:
    """One fenced code block lifted out of a markdown document.

    Attributes:
        doc: The markdown file the block came from.
        line: The 1-based line number of the opening fence.
        lang: The fence info string (e.g. ``"python"``).
        body: The raw block contents, without the fences.
    """

    doc: str
    line: int
    lang: str
    body: str

    @property
    def location(self) -> str:
        """Return a ``file:line`` label for diagnostics.

        Returns:
            A ``"<doc>:<line>"`` string identifying the block.
        """
        return f"{self.doc}:{self.line}"


def _extract_blocks() -> list[DocBlock]:
    """Pull every fenced code block out of the scanned doc files.

    Returns:
        A list of :class:`DocBlock` instances in document order.
    """
    blocks: list[DocBlock] = []
    for rel in DOC_FILES:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for match in re.finditer(
            r"^```(\w*)\n(.*?)^```", text, re.DOTALL | re.MULTILINE
        ):
            blocks.append(
                DocBlock(
                    doc=rel,
                    line=text[: match.start()].count("\n") + 1,
                    lang=match.group(1),
                    body=match.group(2),
                )
            )
    return blocks


ALL_BLOCKS = _extract_blocks()
PYTHON_BLOCKS = [b for b in ALL_BLOCKS if b.lang == "python"]


# ----------------------------------------------------------------------
# Classification registry
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class BlockSpec:
    """How to exercise one documented python block.

    Attributes:
        marker: A substring unique to exactly one python block across all
            scanned docs.
        preamble: Python source executed in the block's namespace before
            the block itself (e.g. to materialise a file the block
            reads).
        raises: When set, the block is expected to raise this exception
            type and is run inside :func:`pytest.raises`.
    """

    marker: str
    preamble: str = ""
    raises: type[BaseException] | None = None


#: The MT942 sample the README Quick Start binds to ``mt942``; reused as
#: a preamble for the file-reading block so it can be written to disk.
_README_SAMPLE = """:20:MT942REF001
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


BLOCK_SPECS: tuple[BlockSpec, ...] = (
    # README — Quick Start: parse a string into transactions.
    BlockSpec(marker="transactions = load_mt942(mt942)"),
    # README — read from a file instead of a string. The block calls
    # ``load_mt942_file("statement.mt942")``; materialise that file.
    BlockSpec(
        marker='load_mt942_file("statement.mt942")',
        preamble=(
            "from pathlib import Path\n"
            f"Path('statement.mt942').write_text({_README_SAMPLE!r}, "
            "encoding='utf-8')\n"
        ),
    ),
    # README — Summaries: bind ``mt942`` first, then summarize it.
    BlockSpec(
        marker="summary = summarize_mt942(mt942)",
        preamble=f"mt942 = {_README_SAMPLE!r}\n",
    ),
    # README — Errors: the snippet is expected to raise ValueError. It
    # uses ``load_mt942`` without re-importing, so supply the import.
    BlockSpec(
        marker='load_mt942(":25:ACC',
        preamble=("from bankstatementparser_loader_mt942 import load_mt942\n"),
        raises=ValueError,
    ),
)


def _matching_blocks(spec: BlockSpec) -> list[DocBlock]:
    """Return every python block whose body contains ``spec.marker``.

    Args:
        spec: The classification entry to match against.

    Returns:
        The matching :class:`DocBlock` list (ideally length one).
    """
    return [b for b in PYTHON_BLOCKS if spec.marker in b.body]


# ----------------------------------------------------------------------
# Structural guarantees
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "block", PYTHON_BLOCKS, ids=[b.location for b in PYTHON_BLOCKS]
)
def test_python_block_is_valid_syntax(block: DocBlock) -> None:
    """Every documented python block parses as valid Python."""
    ast.parse(block.body, filename=block.location)


def test_every_python_block_is_classified() -> None:
    """Each documented python block maps to exactly one BlockSpec."""
    unmatched = [
        b.location
        for b in PYTHON_BLOCKS
        if not any(spec.marker in b.body for spec in BLOCK_SPECS)
    ]
    assert not unmatched, (
        "Unclassified python blocks in docs (add a BlockSpec so the "
        f"example is executed by the regression suite): {unmatched}"
    )

    for spec in BLOCK_SPECS:
        matches = _matching_blocks(spec)
        assert len(matches) == 1, (
            f"BlockSpec marker {spec.marker!r} must match exactly one "
            f"block, matched {[b.location for b in matches]}"
        )


# ----------------------------------------------------------------------
# Execution
# ----------------------------------------------------------------------


def _spec_id(spec: BlockSpec) -> str:
    """Return a readable test id for a BlockSpec.

    Args:
        spec: The classification entry to label.

    Returns:
        The matched block's ``file:line`` label, or the marker prefix
        if no block matched (which the structural test will flag).
    """
    blocks = _matching_blocks(spec)
    return blocks[0].location if blocks else spec.marker[:30]


@pytest.mark.parametrize(
    "spec", BLOCK_SPECS, ids=[_spec_id(s) for s in BLOCK_SPECS]
)
def test_documented_python_block(
    spec: BlockSpec,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Execute one documented python block end-to-end."""
    blocks = _matching_blocks(spec)
    assert len(blocks) == 1
    block = blocks[0]

    monkeypatch.chdir(tmp_path)
    namespace: dict[str, object] = {"__name__": "mt942_doc_example"}
    if spec.preamble:
        exec(
            compile(spec.preamble, f"{block.location}-preamble", "exec"),
            namespace,
        )

    code = compile(block.body, block.location, "exec")
    if spec.raises is not None:
        with pytest.raises(spec.raises):
            exec(code, namespace)
    else:
        exec(code, namespace)
    capsys.readouterr()  # documented examples are allowed to print
