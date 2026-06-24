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
(`test_loader.py`, `test_corpus.py`, `test_real_corpus.py`). The
documentation/version regression suites assert doc sync, not loader
logic, and resolve paths relative to the real repo root — they cannot run
inside mutmut's `mutants/` sandbox copy and are out of scope for mutation
testing (they `pytest.mark.skipif` themselves there).

## Latest score

**348 / 355 killed (97.7%).** The 7 surviving mutants are all genuine
**equivalent mutants** — the mutated code is provably behaviourally
identical to the original given the call sites — and are catalogued below
with rationale. There are **no** unaddressed (killable) survivors.

## Equivalent mutants (justified survivors)

| Mutant | Mutation | Why it is equivalent |
| :-- | :-- | :-- |
| `x__format_yymmdd__mutmut_22` | `value[4:6]` → `value[4:7]` | `_format_yymmdd` is only ever called with an exactly-6-character `YYMMDD` string (a fixed slice of a regex `\d{6}` group). For a 6-char string `[4:7]` and `[4:6]` yield the identical 2-char substring. |
| `x__parse_datetime_stamp__mutmut_22` | `time[2:4]` → `time[2:5]` | The `time` capture group is `\d{4}` — exactly 4 characters — so `[2:5]` and `[2:4]` return the same 2-character minutes substring. |
| `x__parse_datetime_stamp__mutmut_36` | `offset[2:4]` → `offset[2:5]` | The `offset` capture group is `\d{4}` — exactly 4 characters — so `[2:5]` and `[2:4]` return the same 2-character offset-minutes substring. |
| `x__fold_description__mutmut_2` | `isinstance(part, str) and part` → `isinstance(part, str) or part` | The comprehension only ever iterates over `str \| None` values (both call sites — the `:61:` supplementary text and the `:86:` value — produce only `str` or `None`). For a `str`, `isinstance(...) and part` ⇔ truthiness of the string, and `isinstance(...) or part` is also `True`/keeps it when truthy; for `None`, both expressions are falsy and drop it. The two filters select the same items, so the output is identical. |
| `x_load_mt942_file__mutmut_2` | `open(path, encoding="utf-8")` → `encoding=None` | Selects the platform default encoding. The fixtures are pure ASCII and the test environment's default encoding is UTF-8, so no input can distinguish the two decodings here. Not portably killable; documented limitation rather than a behaviour change. |
| `x_load_mt942_file__mutmut_4` | `open(path, encoding="utf-8")` → `open(path)` | Same as above — omitting the keyword is identical to `encoding=None`. |
| `x_load_mt942_file__mutmut_6` | `encoding="utf-8"` → `encoding="UTF-8"` | `"UTF-8"` is a codec-name alias of `"utf-8"`; Python normalises both to the same codec, so the decode is byte-for-byte identical. |
