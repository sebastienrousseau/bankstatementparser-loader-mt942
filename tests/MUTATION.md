# Mutation testing

We run [`mutmut`](https://github.com/boxed/mutmut) over the loader package
to answer the "100% line coverage is weak evidence" objection: coverage
proves every line *executed*, mutation testing proves the test suite
*detects* injected faults.

## How to run

```bash
make mutation          # mutmut run + results
# or
mutmut run
mutmut results
```

The mutation runner targets only the behavioural loader suites
(`test_loader.py`, `test_corpus.py`, `test_real_corpus.py`,
`test_amount_validation.py`, `test_line_endings.py`,
`test_debit_credit_marks.py`, `test_statement_parser_summary.py`),
listed in `[tool.mutmut]` with mutmut 3's
`pytest_add_cli_args_test_selection`; `--no-cov` keeps the suite's
coverage floor out of the mutant runs. The
documentation/version regression suites assert doc sync, not loader
logic, and resolve paths relative to the real repo root — they cannot run
inside mutmut's `mutants/` sandbox copy and are out of scope for mutation
testing (they `pytest.mark.skipif` themselves there).

## Latest score

**427 / 438 killed (97.5%),** run on 2026-11-27 (0.0.36) with mutmut
3.8. The 11 surviving mutants are all genuine **equivalent mutants**
(the mutated code is provably behaviourally identical to the original
given the call sites) and are catalogued below with rationale. There
are **no** unaddressed (killable) survivors.

The total grew from 355 because `Mt942StatementParser` and `_amounts.py`
are mutated too; `test_statement_parser_summary.py` pins
`get_summary` field by field. Before 0.0.36 the configuration used
mutmut 2.x keys (`paths_to_mutate`, `runner`) that mutmut 3 ignores, so
`make mutation` ran every test in the sandbox, failed its stats run and
tried no mutant.

## Equivalent mutants (justified survivors)

| Mutant | Mutation | Why it is equivalent |
| :-- | :-- | :-- |
| `x__format_yymmdd__mutmut_24` | `value[4:6]` → `value[4:7]` | `_format_yymmdd` is only ever called with an exactly-6-character `YYMMDD` string (a fixed slice of a regex `\d{6}` group). For a 6-char string `[4:7]` and `[4:6]` yield the identical 2-char substring. |
| `x__parse_datetime_stamp__mutmut_22` | `time[2:4]` → `time[2:5]` | The `time` capture group is `\d{4}` — exactly 4 characters — so `[2:5]` and `[2:4]` return the same 2-character minutes substring. |
| `x__parse_datetime_stamp__mutmut_36` | `offset[2:4]` → `offset[2:5]` | The `offset` capture group is `\d{4}` — exactly 4 characters — so `[2:5]` and `[2:4]` return the same 2-character offset-minutes substring. |
| `x__fold_description__mutmut_2` | `isinstance(part, str) and part` → `isinstance(part, str) or part` | The comprehension only ever iterates over `str \| None` values (both call sites — the `:61:` supplementary text and the `:86:` value — produce only `str` or `None`). For a `str`, `isinstance(...) and part` ⇔ truthiness of the string, and `isinstance(...) or part` is also `True`/keeps it when truthy; for `None`, both expressions are falsy and drop it. The two filters select the same items, so the output is identical. |
| `x_load_mt942_file__mutmut_2` | `open(path, encoding="utf-8")` → `encoding=None` | Selects the platform default encoding. The fixtures are pure ASCII and the test environment's default encoding is UTF-8, so no input can distinguish the two decodings here. Not portably killable; documented limitation rather than a behaviour change. |
| `x_load_mt942_file__mutmut_4` | `open(path, encoding="utf-8")` → `open(path)` | Same as above — omitting the keyword is identical to `encoding=None`. |
| `x_load_mt942_file__mutmut_6` | `encoding="utf-8"` → `encoding="UTF-8"` | `"UTF-8"` is a codec-name alias of `"utf-8"`; Python normalises both to the same codec, so the decode is byte-for-byte identical. |
| `x_load_mt942_file__mutmut_6` | `encoding="utf-8"` → `encoding="UTF-8"` | Python's codec lookup is case-insensitive; both names select the same codec. |
| `x__split_reference__mutmut_9` | `if sep` → `if sep or True` | Without a `//` separator `customer_ref` is `""`, so the mutant's `"".strip()` is `""`, and the function returns `reference or None`, which is `None` either way. |
| `x__fold_description__mutmut_4` | `if parts` → `if parts or True` | With no parts the mutant returns `""` instead of `None`; `Transaction.from_record` stores an empty description as `None`, so the loaded transaction is identical. |
| `xǁMt942StatementParserǁget_summary__mutmut_4` | `read_text(encoding="utf-8")` → `encoding=None` | As for `load_mt942_file`: identical on a UTF-8 platform with ASCII fixtures, and the file was already decoded as UTF-8 by `parse` just before. |
| `xǁMt942StatementParserǁget_summary__mutmut_7` | `encoding="utf-8"` → `"UTF-8"` | Case-insensitive codec lookup, as above. |
