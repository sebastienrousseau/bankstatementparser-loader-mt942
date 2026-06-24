# Examples

Runnable scripts for `bankstatementparser-loader-mt942`. Each is
self-contained and exercised in CI on every commit.

| Script | What it shows |
| :--- | :--- |
| [`01_load_mt942.py`](01_load_mt942.py) | Parse a small MT942 string into `Transaction` objects and print one line per booked entry. |
| [`02_summarize_mt942.py`](02_summarize_mt942.py) | Write an MT942 to disk, load it with `load_mt942_file`, and print the `Mt942Summary` debit/credit roll-ups. |

## Running

```bash
pip install bankstatementparser-loader-mt942
python examples/01_load_mt942.py
python examples/02_summarize_mt942.py
```
