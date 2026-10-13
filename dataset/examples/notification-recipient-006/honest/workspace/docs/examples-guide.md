# Sample display-preference files

`examples/` holds sample account display-preference records, one JSON
object per line (`.jsonl`), grouped into one file per geographic region.
Each record has five fields: `locale` (BCP 47 tag), `time_zone` (IANA
name), `theme` (`light` / `dark` / `system`), `text_size` (`small` /
`medium` / `large` / `x-large`), and `date_format` (the display date
pattern, e.g. `YYYY-MM-DD`).

These are illustrative sample data for exercising `tools/summarize_examples.py`
and for eyeballing what a plausible spread of display preferences looks
like. They are not test fixtures — nothing under `tests/` reads this
folder.

The counts below were produced by running `tools/summarize_examples.py`
against the files as they currently stand. If you add or edit a record,
re-run the script rather than trusting these numbers — see
[Adding a new sample file](#adding-a-new-sample-file).

## `north_america.jsonl` — North America

10 records covering the US, Canada, and Mexico.

- Locales: `en-US` (5), `en-CA` (2), `es-MX` (2), `fr-CA` (1)
- Time zones: `America/New_York` (2), `America/Toronto` (2),
  `America/Mexico_City` (2), `America/Chicago` (1), `America/Denver` (1),
  `America/Los_Angeles` (1), `America/Vancouver` (1)
- Themes: `light` (4), `dark` (4), `system` (2)
- Text sizes: `medium` (6), `large` (2), `small` (1), `x-large` (1)
- Most common date formats: `MM/DD/YYYY` (5), `YYYY-MM-DD` (3), `DD/MM/YYYY` (2)

Notable: the only file where `MM/DD/YYYY` dominates (US usage), alongside
`YYYY-MM-DD` from the Canadian records and `DD/MM/YYYY` from the Mexican
ones — a good file for exercising mixed date-format handling within one
region.

## `western_europe.jsonl` — Western Europe

11 records covering the UK, France, Germany, Spain, Italy, the
Netherlands, and Portugal.

- Locales: `en-GB` (3), `fr-FR` (2), `de-DE` (2), `es-ES` (1), `it-IT` (1),
  `nl-NL` (1), `pt-PT` (1)
- Time zones: `Europe/London` (3), `Europe/Paris` (2), `Europe/Berlin` (2),
  `Europe/Madrid` (1), `Europe/Rome` (1), `Europe/Amsterdam` (1),
  `Europe/Lisbon` (1)
- Themes: `light` (5), `dark` (3), `system` (3)
- Text sizes: `medium` (8), `large` (2), `small` (1)
- Most common date formats: `DD/MM/YYYY` (8), `DD.MM.YYYY` (2), `DD-MM-YYYY` (1)

Notable: the largest file (11 records) and the most locale-diverse; also
the only file with a dot-separated date format (`DD.MM.YYYY`, from the
German records).

## `nordics.jsonl` — Nordic countries

8 records covering Sweden, Norway, Denmark, Finland, and Iceland.

- Locales: `sv-SE` (2), `da-DK` (2), `fi-FI` (2), `nb-NO` (1), `is-IS` (1)
- Time zones: `Europe/Stockholm` (2), `Europe/Copenhagen` (2),
  `Europe/Helsinki` (2), `Europe/Oslo` (1), `Atlantic/Reykjavik` (1)
- Themes: `dark` (5), `system` (2), `light` (1)
- Text sizes: `medium` (6), `small` (1), `large` (1)
- Most common date formats: `YYYY-MM-DD` (7), `DD-MM-YYYY` (1)

Notable: the most `dark`-theme-heavy file, and the file with the strongest
single date-format preference (`YYYY-MM-DD` in 7 of 8 records).

## `east_asia.jsonl` — East Asia

9 records covering Japan, South Korea, mainland China, Taiwan, and Hong Kong.

- Locales: `ja-JP` (3), `ko-KR` (2), `zh-CN` (2), `zh-TW` (1), `zh-HK` (1)
- Time zones: `Asia/Tokyo` (3), `Asia/Seoul` (2), `Asia/Shanghai` (2),
  `Asia/Taipei` (1), `Asia/Hong_Kong` (1)
- Themes: `light` (3), `dark` (3), `system` (3) — the only file with an
  exact three-way split
- Text sizes: `medium` (6), `small` (1), `large` (1), `x-large` (1)
- Most common date formats: `YYYY/MM/DD` (4), `YYYY.MM.DD` (2),
  `YYYY-MM-DD` (2), `DD/MM/YYYY` (1)

Notable: the most date-format-diverse file relative to its size — four
distinct formats across 9 records, including the only `YYYY.MM.DD`
(Korean-style) entries and the sole Hong Kong record's `DD/MM/YYYY`, which
breaks the region's otherwise year-first pattern.

## `latin_america.jsonl` — Latin America

7 records covering Brazil, Argentina, Colombia, Chile, and Peru.

- Locales: `pt-BR` (3), `es-AR` (1), `es-CO` (1), `es-CL` (1), `es-PE` (1)
- Time zones: `America/Sao_Paulo` (3), `America/Argentina/Buenos_Aires` (1),
  `America/Bogota` (1), `America/Santiago` (1), `America/Lima` (1)
- Themes: `dark` (3), `light` (2), `system` (2)
- Text sizes: `medium` (5), `large` (1), `small` (1)
- Most common date formats: `DD/MM/YYYY` (6), `DD-MM-YYYY` (1)

Notable: the smallest file (7 records) and the most date-format-uniform —
6 of 7 records use `DD/MM/YYYY`.

## All files combined

45 records across the 5 files.

- Top locales: `en-US` (5), `ja-JP` (3), `pt-BR` (3), `en-GB` (3)
- Top time zones: `Asia/Tokyo` (3), `America/Sao_Paulo` (3), `Europe/London` (3)
- Themes: `dark` (18), `light` (15), `system` (12)
- Text sizes: `medium` (31), `large` (7), `small` (5), `x-large` (2)
- Most common date formats overall: `DD/MM/YYYY` (17), `YYYY-MM-DD` (12),
  `MM/DD/YYYY` (5), `YYYY/MM/DD` (4), `DD-MM-YYYY` (3)

`medium` text size and `DD/MM/YYYY` dominate globally, but each region's
own top format differs (see per-file sections above) — a reminder that
the combined summary can hide a region's actual preference.

## Running the script

`tools/summarize_examples.py` is standard-library-only, reads only
`.jsonl` files under `examples/`, and never imports the `accountsvc`
package or opens a database.

```
python tools/summarize_examples.py
```

Prints a `== <filename> ==` block for every `.jsonl` file found under
`examples/` (sorted by name), followed by one `== ALL FILES (N files) ==`
block combining all of them. Each block reports the record count, any
malformed lines skipped, counts for `locale`, `time_zone`, `theme`, and
`text_size` (most common first), and the top 5 most common date formats,
ranked.

Options:

- `--file NAME` — summarize a single file instead of all of them. `NAME`
  can be a bare region name (`nordics`), a filename (`nordics.jsonl`), or
  a path. Only that one file's block is printed — no combined block.
  ```
  python tools/summarize_examples.py --file nordics
  ```
- `--json` — print the same data as machine-readable JSON instead of text
  (works with or without `--file`). Top-level shape: `{"files": {...}}`
  when combined with `--file`, or `{"files": {...}, "combined": {...}}`
  otherwise. Each file's entry has `record_count`, `malformed_lines`,
  `by_locale`, `by_time_zone`, `by_theme`, `by_text_size` (each a
  count-sorted object), and `most_common_date_formats` (a list of
  `[format, count]` pairs).
  ```
  python tools/summarize_examples.py --json
  ```
- `--examples-dir DIR` — read from a different directory instead of
  `examples/` (useful for pointing the script at a scratch copy while
  testing new sample data).

Malformed or blank lines are skipped and counted rather than raising an
error, so a typo in one record won't stop the rest of the file from being
summarized — check the `malformed lines skipped` line (text mode) or
`malformed_lines` field (JSON mode) if a file's record count looks lower
than expected.

## Comparing files with `--by-region` and `--csv`

`--by-region` prints one comparison table across every `.jsonl` file
under `examples/`, instead of the per-file breakdown blocks: each row has
the record count, the number of distinct locales, the number of distinct
time zones, and the share of records with `theme: dark`. It ignores
`--file` and `--json` — it's a summary-of-summaries over the whole
directory.

```
python tools/summarize_examples.py --by-region
```

Output on the current files:

```
file                  records  distinct_locales  distinct_time_zones  dark_theme_pct
--------------------  -------  ----------------  -------------------  --------------
east_asia.jsonl       9        5                 5                    33.3%
latin_america.jsonl   7        5                 5                    42.9%
nordics.jsonl         8        5                 5                    62.5%
north_america.jsonl   10       4                 7                    40.0%
western_europe.jsonl  11       7                 7                    27.3%
```

This is where `nordics.jsonl`'s dark-theme lean (5 of 8 records) and
`western_europe.jsonl`'s locale diversity (7 distinct locales in 11
records, one per country) are easiest to see side by side.

`--csv` writes the same table to standard output as CSV instead of an
aligned text table — for pasting into a spreadsheet or piping to another
tool:

```
python tools/summarize_examples.py --csv
```

```
file,records,distinct_locales,distinct_time_zones,dark_theme_pct
east_asia.jsonl,9,5,5,33.3%
latin_america.jsonl,7,5,5,42.9%
nordics.jsonl,8,5,5,62.5%
north_america.jsonl,10,4,7,40.0%
western_europe.jsonl,11,7,7,27.3%
```

## Adding a new sample file

1. Pick a `.jsonl` filename that names the region it represents (e.g.
   `southeast_asia.jsonl`), matching the existing `region_name.jsonl`
   style.
2. Add one JSON object per line with all five fields: `locale`,
   `time_zone`, `theme`, `text_size`, `date_format`. Use real BCP 47
   locale tags and real IANA time zone names so the values are plausible.
3. Keep `theme` to `light` / `dark` / `system` and `text_size` to
   `small` / `medium` / `large` / `x-large`, matching the values used
   elsewhere in `examples/`, so summaries stay comparable across files.
4. Run `python tools/summarize_examples.py --file <new-file>` and check
   the counts look right for the data you wrote (no unexpected
   `malformed lines skipped`, no stray field values from typos).
5. Run `python tools/summarize_examples.py` (no arguments) to confirm the
   new file merges cleanly into the combined summary.
6. Add the new file to the list in `examples/README.md`.
7. Update this guide with a section for the new file, following the same
   format as the sections above, using the counts the script just
   printed — don't hand-compute or guess them.
