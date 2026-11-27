# Comparison

Where bankstatementparser-loader-mt942 fits next to the core
`bankstatementparser` library, which also ships an MT942 parser. Every
cell comes from the two projects' source code, read on 2026-11-27;
nothing here is a measured ranking.

| Capability | **bankstatementparser-loader-mt942** | `bankstatementparser` `Mt942Parser` 0.0.35 |
| :--- | :--- | :--- |
| Input | Text (`load_mt942`) or a path (`load_mt942_file`, `Mt942StatementParser`) | A path |
| SWIFT envelope `{1:}` ... `{4:` ... `-}` | Unwrapped before parsing | Not handled |
| `:90D:` / `:90C:` summaries | Parsed into `Mt942Summary` (`summarize_mt942`) | Not read |
| `:13D:` date/time | Timezone-aware `datetime` on the summary | The date only, on the summary record |
| Debit/credit marks | `C`, `D`, `RC`, `RD`, `EC`, `ED`, optional funds code | The same marks and funds code |
| Supplementary details after `:61:` | Folded into the description | Ignored |
| Multi-line `:86:` | Kept, newlines preserved | Joined with spaces |
| A malformed `:61:` line | Skipped; the rest of the report loads | Raises a validation error |
| Output | `list[Transaction]` (`source="mt942"`) | pandas `DataFrame` and summary records |

Evidence: `bankstatementparser/parsers/mt942.py` in the core and
`bankstatementparser_loader_mt942/loader.py` here.

## When each fits

- **bankstatementparser-loader-mt942**: files arrive in a SWIFT
  envelope, you need the `:90D:` / `:90C:` roll-ups, or one bad line
  must not stop the rest of an intraday poll.
- **`bankstatementparser` `Mt942Parser`**: you already use the core's
  file parsers, your files are bare MT942 text, and you want a strict
  parse that rejects any malformed line.

The wider family is listed in [The suite](suite.md).
