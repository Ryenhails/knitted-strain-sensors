# Reference values

What the paper printed, used by `scripts/5_verify.py`. The source is the
submitted version of the paper (LaTeX source and figure PDFs of 27 Oct 2026).

| File | Contents | How it was obtained |
|---|---|---|
| `paper_table4.csv` | every cell of Table IV, as printed | parsed from the table `\label{tab:designs}` in the `.tex` |
| `paper_table5.csv` | every cell of Table V, as printed | parsed from the table `\label{tab:ml}` |
| `paper_fig6.csv` | ρ and 95 % interval of the 12 points of Fig. 6 | read from the vector drawing in `figures/cross.pdf`, converted to data units with the axis ticks (3 decimals) |
| `paper_fig7.csv` | the same for the 36 points of Fig. 7 | from `figures/rq2.pdf` |
| `paper_text_values.csv` | the 94 numbers quoted in the text | written by hand, one row per number |

**Columns of `paper_text_values.csv`:**

* `paper_text`: the sentence the number comes from.
* `key`: where the regenerated value is, in `results/numbers_section5.json` or
  `numbers_section6.json`. For example, `V-A.rate.mean_by_rate.GF.A` is the mean GF
  at the slow rate in Section V-A.
* `printed`: the value as printed.
* `mode`: how the two are compared:
  * `num`: equal within half a unit of the last printed digit, or within `tol` if
    one is given;
  * `lt`: the regenerated value is below the printed bound;
  * `eq` / `set`: the same design name, or the same set of names;
  * `count`: the number of list entries.
* `known_issue`: filled in where the paper's text is imprecise. Such checks are
  listed separately in the report.
