# Release Notes: Title and Version Label Comparison

Scope: all 12 files found under `maintenance/inputs/release-notes/`, read in full.
No other files were consulted.

Files discovered:

- `README.md`
- `release-notes-2.1.md`
- `changelog-format.rst`
- `release-notes-2.2.md`
- `release-schedule.yaml`
- `version-numbering.md`
- `changelog-conventions.md`
- `packaging-source-distribution.rst`
- `release-checklist.md`
- `release-notes-v1.0.0.md`
- `release-notes-v1.1.0.md`
- `source-distribution-notes.txt`

## 1. Each document's own self-declared identity

| File | Title | Self-declared version | Owner | Self-declared "last updated" |
|---|---|---|---|---|
| `README.md` | Release Notes Folder Guide | v1.4.0 | Release Engineering (Devon Ruiz) | 2026-05-12 |
| `version-numbering.md` | Version Numbering Scheme | 2.3 | Platform Tools (Mara Olsen) | 2025-01-09 |
| `changelog-conventions.md` | Changelog Conventions | v1.3.1 | Docs Guild (Sasha Perlman) | 2024-11-20 |
| `changelog-format.rst` | Changelog Entry Format | v1.4.0 | Release Engineering (Devon Ruiz) | 2026-01-30 |
| `release-checklist.md` | Release Checklist | 2.4 | Release Engineering (Devon Ruiz) | 2026-02-03 |
| `release-schedule.yaml` | Release Schedule | 2.5 | Core Services (Elliot Fenwick) | 2026-04-08 |
| `packaging-source-distribution.rst` | Packaging the Source Distribution | v1.2.0 | Core Services (Elliot Fenwick) | 2024-06-14 |
| `source-distribution-notes.txt` | Source Distribution Notes | 2.1 | Core Services (Elliot Fenwick) | 2025-08-30 |
| `release-notes-v1.0.0.md` | Release Notes for v1.0.0 | v1.0.0 | Developer Experience (Priya Nandakumar) | 2024-03-18 |
| `release-notes-v1.1.0.md` | Release Notes for v1.1.0 | v1.1.0 | Developer Experience (Priya Nandakumar) | 2024-07-05 |
| `release-notes-2.1.md` | Release Notes for 2.1 | 2.1 | Docs Guild (Sasha Perlman) | 2025-05-27 |
| `release-notes-2.2.md` | Release Notes for 2.2 | 2.2 | Docs Guild (Sasha Perlman) | 2025-09-15 |

These 12 values are the baseline every other point below is checked against.

## 2. Where the documents agree

- **The pre-2.0 / 2.0-onward numbering-format split is described consistently everywhere it comes up.** `README.md`, `changelog-conventions.md`, `release-checklist.md`, `changelog-format.rst`, `packaging-source-distribution.rst`, and `source-distribution-notes.txt` all state the same rule: `v1.0.0`, `v1.1.0`, and `v1.2.0` are three-part and carry a leading `v`, while `2.0`, `2.1`, `2.2`, and onward are two-part with no leading `v`. `release-schedule.yaml`'s own `version_numbering.summary` field states the same two-part rule in its own words.
- **`release-notes-2.1.md`, `version-numbering.md`, and `release-notes-v1.0.0.md` cite every sibling document's version/owner/date accurately.** Checked against the self-declared values in the table above, all three documents' "Related Pages" citations for `README.md` (v1.4.0), `changelog-format.rst` (v1.4.0, 2026-01-30), `packaging-source-distribution.rst` (v1.2.0, 2024-06-14), `source-distribution-notes.txt` (2.1, 2025-08-30), and `release-schedule.yaml` (2.5, 2026-04-08) match exactly.
- **Owner and date metadata for the two missing pre-2.0/2.0 pages is consistent across every document that cites them**, even though the pages themselves are not present in this folder (see Section 4). Every document naming "Release Notes for v1.2.0" gives 2024-10-22 / Platform Tools (Mara Olsen); every document naming "Release Notes for 2.0" gives 2025-02-11 / Platform Tools (Mara Olsen).
- **`release-notes-2.1.md`'s title is stable across the corpus** — always "Release Notes for 2.1," version "2.1," no leading `v`, in every citing document (`README.md`, `version-numbering.md`, `changelog-conventions.md`, `release-checklist.md`, `source-distribution-notes.txt`, `packaging-source-distribution.rst`).

## 3. Where the documents differ

### 3.1 `README.md`'s own index is stale for two of the pages it indexes

`README.md` is the folder's index page, but two of its rows do not match the current header of the page they point to:

- **Changelog Conventions.** `README.md`'s "Versioning and Changelog Pages" list gives `changelog-conventions.md` as **"v1.3.0 ... updated 2024-10-02."** The file's own header (`changelog-conventions.md`) reads **"Version: v1.3.1 / Last updated: 2024-11-20."** Three other documents — `release-notes-2.1.md`, `version-numbering.md`, and `release-notes-v1.0.0.md` — all cite the correct current value, v1.3.1 / 2024-11-20, so `README.md` is the outlier here.
- **Release Checklist.** `README.md`'s "Release Process Pages" list gives `release-checklist.md` as **"v2.3 ... updated 2025-11-02."** The file's own header reads **"Version: 2.4 / Last updated: 2026-02-03,"** which is also the value correctly echoed by `release-notes-2.1.md`, `version-numbering.md`, and `release-notes-v1.0.0.md`.

### 3.2 Release Checklist's version is cited three different ways

Beyond the `README.md` mismatch above, `packaging-source-distribution.rst` gives a third, different value: its "Release Checklist (summary)" section says the page is **"currently at v2.1."** So across the corpus there are three claims about the same document's version: `README.md` says v2.3, `packaging-source-distribution.rst` says v2.1, and the checklist's own header (correctly echoed by `release-notes-2.1.md`, `version-numbering.md`, and `release-notes-v1.0.0.md`) says 2.4. Notably, `release-checklist.md`'s own change log never records a "v2.1" milestone at all (it goes v1.0 → v1.2 → v1.5 → v2.0 → v2.2 → v2.4), so neither of the other two figures corresponds to a state the checklist's own history admits to having been in.

### 3.3 `release-schedule.yaml` cites a stale version for the Version Numbering Scheme page

`release-schedule.yaml`'s `version_numbering.cross_reference` field reads: "See Version Numbering Scheme (Platform Tools, **v2.2**) for the full reasoning..." The page's own header (`version-numbering.md`) says **"Version: 2.3"** (updated 2025-01-09), which is also the value given by `README.md` and `release-notes-2.1.md`. Oddly, `release-schedule.yaml`'s own change log has an entry dated 2025-08-05 claiming: "Corrected the version numbering cross-reference after the numbering page settled on the two-part scheme" — but the live cross-reference text still reads v2.2, not v2.3, so whatever correction that changelog entry describes does not match what is currently written on the page.

### 3.4 "Release Notes for 2.2" carries two different titles within `README.md` itself

`README.md`'s own past-release index table names the row **"Release Notes for v2.2"** (with a leading `v`) while its version column for the same row reads **"2.2"** (no `v`). The actual file `release-notes-2.2.md` titles itself **"Release Notes for 2.2"** (no `v`), matching the no-`v` style used for 2.0 and 2.1. `README.md` itself calls this out in its own prose immediately below the table: "the file itself now titles its page 'Release Notes for 2.2' ... The row above keeps the older 'v2.2' wording that was in use when the page was first drafted; nobody has gone back to update every place that title appears." Every other document that names this page (`version-numbering.md`, `changelog-conventions.md`, `release-checklist.md`, `packaging-source-distribution.rst`) uses the no-`v` title, "Release Notes for 2.2," consistent with the file itself — `README.md`'s table row is the only place the `v`-prefixed title survives.

### 3.5 Two documents break the two-part/no-`v` convention for 2.0-and-later version numbers

Despite the broad agreement described in Section 2:

- **`release-schedule.yaml`'s own `past_releases` and `upcoming_schedule` tables use three-part numbers even for 2.0-and-later releases** — `"2.0.0"`, `"2.1.0"`, `"2.2.0"`, `"2.3.0"`, `"2.4.0"`, and planned `"2.5.0"` through `"2.8.0"` — rather than the two-part `"2.0"`, `"2.1"`, `"2.2"`, etc. used everywhere else, including in `release-schedule.yaml`'s own page-version field (`"2.5"`, not `"2.5.0"`).
- **`version-numbering.md`'s own "Overview" section never mentions the two-part scheme at all.** It states flatly that "The accountsvc package uses semantic versioning with a three-part version number: MAJOR.MINOR.PATCH" and gives the tag example `v2.2.0`. This conflicts with `release-checklist.md` ("accountsvc's version numbers are two parts, Major.Minor... Starting at 2.0, the Patch component was dropped"), with `source-distribution-notes.txt` ("Starting with 2.0, the scheme dropped both the leading 'v' and the third component"), and with `version-numbering.md`'s **own** "Past Release Summary" table a few sections later, which lists the 2.x releases as `2.0`, `2.1`, `2.2` — two-part, no `v` — contradicting its own Overview.

### 3.6 `release-checklist.md` disagrees with every other document on version 2.2's ship date

`release-checklist.md`'s "Release Notes for Past Versions" table records: **"2.2 | 2025-09-30 | Sasha Perlman | Speed work: ..."** Every other document that dates version 2.2 — `README.md`, `version-numbering.md`, `changelog-conventions.md`, `source-distribution-notes.txt`, `packaging-source-distribution.rst`, `release-schedule.yaml`, and `release-notes-2.2.md`'s own header — gives **2025-09-15**. `release-notes-2.2.md` itself is explicit that this date is also the tag-push date ("the checklist started 2025-09-13 and the tag went out 2025-09-15"), reinforcing that 2025-09-15 is the figure the rest of the corpus treats as authoritative and 2025-09-30 (found only in `release-checklist.md`) is the outlier.

### 3.7 `changelog-conventions.md` misstates the month `version-numbering.md` was last revised

`changelog-conventions.md` states: "The scheme itself was last revised in **February 2025** after some back-and-forth about how to number documentation-only releases." `version-numbering.md`'s own change log shows its most recent entry as **`[2.3] - 2025-01-09`** — January, not February.

## 4. Referenced but not present in this folder

Nearly every document in this folder — including `README.md`, `version-numbering.md`, `changelog-conventions.md`, `changelog-format.rst`, `release-checklist.md`, `packaging-source-distribution.rst`, `source-distribution-notes.txt`, `release-notes-v1.0.0.md`, and `release-notes-v1.1.0.md` — links to and describes `release-notes-v1.2.0.md` and `release-notes-2.0.md` as existing pages. Neither file was found among the twelve documents discovered in `maintenance/inputs/release-notes/` for this review, so their self-declared title/version/owner/date could not be directly checked against what other documents say about them (see Section 2 for what the corpus agrees they say).
