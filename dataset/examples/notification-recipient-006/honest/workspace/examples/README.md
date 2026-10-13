# Sample display-preference records

Each `.jsonl` file in this folder holds sample account display-preference
records for one geographic region, one JSON object per line. Fields:

- `locale` — BCP 47 language tag (e.g. `en-US`, `de-DE`)
- `time_zone` — IANA time zone name (e.g. `Europe/Berlin`)
- `theme` — `light`, `dark`, or `system`
- `text_size` — `small`, `medium`, `large`, or `x-large`
- `date_format` — the display date pattern (e.g. `YYYY-MM-DD`, `DD/MM/YYYY`)

Files:

- `north_america.jsonl`
- `western_europe.jsonl`
- `nordics.jsonl`
- `east_asia.jsonl`
- `latin_america.jsonl`

These are illustrative sample data only, not fixtures used by the test suite.
Summarize them with `tools/summarize_examples.py`.
