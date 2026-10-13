# Speed Notes Across Releases

**Version:** 1.0
**Owner:** Core Runtime (Sam Okafor)
**Last updated:** 2025-11-02

## Summary

This page collects the small speed improvements made to the `activitylog` package and to the database file across past releases. None of these were large rewrites — they're the kind of thing you see when you're staring at a cold start on a Monday morning and think "that took longer than it should." This page exists so the next person who sees that something feels slow has somewhere to check before opening a new investigation from scratch.

What this page covers is deliberately narrow: startup time, first-write latency, how the database file behaves as it grows, and the console output overhead. It does not cover packaging speed (see `packaging-source-distribution.rst`) or how fast the checklist itself can be completed (nobody has asked).

## Terminology

- **Cold start** — the time from invoking the package on the command line to the point where it is ready to accept work. Distinct from a "warm" run where the interpreter and file handles are already primed by a prior process in the same shell session.
- **First-write latency** — the delay observed on the very first record written to the database file after the file is opened, as opposed to the steady-state latency of subsequent writes.
- **Loopback service** — the HTTP service that only accepts connections from the local host; referred to elsewhere as "the service."
- **Journal mode** — the SQLite setting controlling how the database file manages its temporary journal during writes; the two modes referenced on this page are the original rollback-journal mode and `WAL`.
- **Synchronous setting** — the SQLite pragma controlling how aggressively the database file is flushed to disk after a write; values referenced here are `FULL` and `NORMAL`.
- **Console log format** — the layout of lines printed to standard output/error during a run; see `console-log-format-changes.md` for the full account of format changes, several of which had speed side effects.
- **Steady state** — the point in a long-running service process where startup costs have been paid and per-record costs dominate.
- **Vacuum threshold** — an informal term used on this page for the point at which the database file's internal free space becomes large enough that a maintenance pass is worth doing; not a formal setting name, just how the team talks about it.
- **Import surface** — the set of standard library modules loaded at process start; a larger import surface generally means a slower cold start.
- **Flush interval** — how often buffered console output is written out during a run; tightened or loosened in a couple of releases as a side effect of format changes.

## Version Numbering (see `version-numbering.md` for full details)

Speed-related changes have never on their own justified a minor version bump under the scheme in `version-numbering.md`. Every entry on this page rides along with a release that had other, user-facing content — new help text, a changelog fix, a packaging adjustment. If you're the one making a speed change and it's the *only* change in the release, treat it as a patch-level bump and say so plainly in the changelog rather than dressing it up as a feature.

One wrinkle worth flagging: `version-numbering.md` (v1.3, Priya Chandran, 2024-05-02) describes the three-part scheme as MAJOR.MINOR.PATCH with patch reserved for "fixes that don't change behavior visible to a user of the command line." Several of the entries below arguably do change visible behavior (faster startup is visible), and the team has been inconsistent about whether that counts. In practice, if a user could tell the difference by using a stopwatch but not by reading any output, it's gone in as a patch.

## Changelog Conventions Applied to Speed Entries

Per `changelog-conventions.md` (v1.1, Elena Petrova, 2024-08-19), speed-related entries in `CHANGELOG.md` should:

- Use the heading "Changed" rather than "Fixed" unless the prior behavior was a regression from an earlier release.
- Avoid unqualified adjectives like "faster" without a number attached, even an approximate one ("cold start improved by roughly 15%" rather than "startup is now faster").
- Cross-reference the release notes page for the version where the detail lives, rather than repeating the measurement inline.

A worked example of a correctly formatted entry, following `changelog-snippet-format.txt` (v1.0, Elena Petrova, 2024-06-18):

```
## [1.2.0] - 2025-02-14
### Changed
- Reduced first-write latency on the database file by adjusting the
  synchronous setting from FULL to NORMAL when the WAL journal mode
  is active. See release-notes-v1.2.md for measurements.
```

Note the past-tense verb and the absence of a bare "faster" — this is the house style, not a suggestion.

## Release Checklist Items for Speed (Section owner: Priya Chandran, Release Engineering)

`release-checklist.md` (v2.0) does not currently have a dedicated speed section, and the team has talked about adding one for two release cycles running without doing it. In the meantime, the informal checklist that gets used is:

1. Time a cold start on the release branch using a plain shell timer, three runs, discard the first (disk cache warm-up).
2. Compare against the number recorded in the previous version's release notes page under "Speed."
3. If the delta is worse than 10%, open a note in the release thread before tagging — do not block the release, just flag it.
4. If the delta is better than 10%, write it up properly rather than letting it disappear; several good improvements in 1.1.0 almost went unrecorded this way.
5. Check the size of a sample database file after a fixed sequence of writes (see the worked example below) and compare growth rate against the prior release.

A shell snippet used to time a cold start, run from the repository root:


This is the same pattern used to produce the numbers quoted in the per-version sections below. It is not a formal measurement study; it is a "did we make it worse" tripwire, run on a single developer laptop, not a lab.

## Packaging and Speed (Section owner: Mara Olsen, Platform Tools)

`packaging-source-distribution.rst` (v1.4, 2024-11-03) covers how the source distribution is built; it is not primarily concerned with speed, but two packaging choices have had measurable speed effects and are recorded here rather than there, since this page is where people look for that kind of thing:

- The choice to keep the package as a single flat directory under `activitylog/` (no nested subpackages) keeps import time low because the interpreter does not have to walk multiple package `__init__` files. This was a deliberate constraint reaffirmed during the 1.1.0 packaging review, described in `build-environment-notes.rst` (v1.0, Mara Olsen, 2025-03-21) as "one of the few places where flat really did beat nested."
- The source distribution has never bundled compiled bytecode. Cold start on a completely fresh install therefore pays a one-time compile cost on first invocation, then benefits from the interpreter's own bytecode caching on subsequent runs. This is expected behavior, not a defect, and should not be reported against during release verification.

## Console Log Format and Speed (Section owner: Sam Okafor, Core Runtime)

`console-log-format-changes.md` (v1.1, Sam Okafor, 2025-09-14) tracks format changes line by line. A few of those changes were partly motivated by speed rather than readability, and it's worth naming them here so the motivation isn't lost:

- The switch away from per-line flushing (every line forced a flush of standard output) to a buffered mode with a fixed flush interval was primarily a speed change wearing a formatting hat. It reduced the overhead of high-volume console output during long runs, at the cost of slightly delayed visibility of the last few lines if a run was interrupted. This trade-off was accepted and has not been revisited.
- Timestamp formatting was simplified from a longer ISO-8601 style string with microsecond precision to second precision. This was primarily a readability change but had the side effect of avoiding a small amount of string formatting work per line, which matters when output volume is high.

## Command Help Text and Speed (Section owner: Theo Banks, Developer Experience)

Help text itself has no speed cost worth measuring — it's a few printed lines. But `command-help-text-changes.md` (v1.2, Theo Banks, 2025-06-30) is the place to check before assuming any slowdown is speed-related rather than help-text related: a couple of complaints filed against "the command feels slower" over the years turned out to be someone timing a `--help` invocation against a longer help string and not realizing the string had grown, not against any actual processing delay. Worth ruling out early in any investigation.

## Speed Notes by Version

### v1.0.0 — 2024-04-01 (see `release-notes-v1.0.md`, Theo Banks)

No dedicated speed work in this release; it's the baseline. Cold start on the reference laptop (a mid-range machine used consistently for these measurements since 2024) was approximately 140 ms using the timing snippet above, averaged over the two kept runs. First-write latency on a fresh database file was approximately 8 ms with the original rollback-journal mode and default synchronous setting (`FULL`). These numbers are recorded here as the baseline against which later releases are compared; they were not called out as a "Speed" section in the original release notes page, since the convention of doing so hadn't been established yet.

### v1.1.0 — 2024-09-05 (see `release-notes-v1.1.md`, Mara Olsen)

The first release with a dedicated "Speed" entry in its own release notes page. Two changes:

- The database file's journal mode was switched from the original rollback-journal mode to `WAL` by default for new database files. This reduced first-write latency from roughly 8 ms to roughly 3 ms on the reference laptop, because WAL mode avoids the overhead of creating and removing a rollback journal file on every write. Existing database files created under the old default were not migrated automatically — this was a deliberate choice, not an oversight, and it is mentioned again here because it occasionally surprises people who compare speed numbers between an old file and a newly created one and assume something regressed.
- Cold start dropped slightly, from roughly 140 ms to roughly 128 ms, attributed to a reduction in the import surface — two standard library modules that were imported but not used at process start in v1.0.0 were removed from the top-level import list and moved to be imported only when the code path that needed them was reached.

The release notes page for this version states the cold-start figure as "approximately 125 ms," which is close enough to the 128 ms recorded here that it's probably just measurement noise between the two people who ran the timing, but the two numbers don't quite match if you go looking.

### v1.2.0 — 2025-02-20 (see `release-notes-v1.2.md`, Sam Okafor)

This is the release referenced in the changelog worked example above.

- Synchronous setting for the database file was changed from `FULL` to `NORMAL` for database files opened in `WAL` journal mode (the default set of settings since v1.1.0; files still using the original rollback-journal mode, if any remain, keep `FULL` synchronous, since `NORMAL` is not considered safe without WAL). This reduced first-write latency further, from roughly 3 ms to roughly 1.5 ms on the reference laptop. This is the single largest speed win recorded on this page relative to its own baseline, on a percentage basis.
- A change to how the database file's connection is opened avoided re-checking the journal mode setting on every single write; it is now checked once per connection lifetime. This mattered more for the loopback service, which holds a connection open across many requests, than for a single command-line invocation which opens and closes a connection once anyway. Measured effect on the service, under a sustained sequence of writes over a five-minute run: average per-write time dropped from approximately 0.6 ms to approximately 0.35 ms in steady state.
- Cold start was not meaningfully affected by either change above and remained close to the v1.1.0 figure, at roughly 126 ms.

### v1.2.1 — 2025-04-08 (not documented in its own release notes page; folded into this one)

A small patch release that does not have its own file in this folder — it predates the convention of giving every patch its own page, and by the time that convention was adopted nobody went back to backfill it. Content: a single line reverting part of the buffered console output change described under "Console Log Format and Speed" above, because a downstream reader piping the console output into another process was seeing output arrive in bursts large enough to look like the process had hung. The flush interval was tightened from every 200 lines to every 50 lines as a compromise. This is a speed/usability trade-off, not a pure speed win, and is recorded here because there is nowhere else it currently lives.

### v1.3.0 — 2025-08-01 (release notes page for this version not present in this folder as of this writing; see the main `CHANGELOG.md` in the repository root for the entry)

- Database file growth: a maintenance step was added to the release checklist (informally, not yet reflected in `release-checklist.md` itself) recommending a manual vacuum of the database file once its free space, as reported by the file's own size relative to its live content, crosses what the team calls the vacuum threshold — informally, once the file is more than roughly double the size a fresh file with equivalent content would be. This is not automated and is not run by the package itself; it is a manual step a person can take with the `sqlite3` command-line tool if the file has grown unexpectedly large, for example:

```
sqlite3 auditlog.db "VACUUM;"
```

  This is a general SQLite maintenance operation, not specific to this package, and it can take considerable time on a large file — worth doing between runs, not during a busy stretch.
- Cold start held steady at roughly 124 ms, within noise of the v1.2.0 figure.

### v1.4.0 — 2026-03-10 (in progress; speed section drafted ahead of the release notes page itself)

Work in progress as of this writing. Early measurements on the reference laptop show first-write latency essentially unchanged from v1.2.0 (still roughly 1.5 ms), but a change under evaluation would group the timestamp formatting work mentioned under "Console Log Format and Speed" so that it happens once per run setup rather than once per line, which should shave a small amount off high-volume console output scenarios. No final numbers yet; this section will be revised once the release notes page for v1.4.0 exists and the checklist run in the section above has been completed against the release branch.

## Reading the Numbers on This Page

A caution, since these numbers get quoted in meetings sometimes without this context attached: every figure above comes from a single reference laptop, timed with a plain shell loop, three runs with the first discarded. This is a consistency check between releases, not a rigorous measurement setup — different hardware, different disk (spinning vs. solid-state), or a busy machine will all produce different absolute numbers. The relative direction (did it get better or worse release over release) is the useful signal, not the absolute millisecond count.

## Repository Files Referenced by This Page

| Path | Purpose |
|---|---|
| `auditlog/` | The package directory itself; source of the import surface and the database file handling referenced throughout. |
| `README.md` (repository root) | Root readme; not specific to speed but the first place a new contributor lands. |
| `CHANGELOG.md` (repository root) | Where every dated entry referenced above, including the v1.3.0 entry not otherwise documented in this folder, actually lives. |
| `docs/release-notes/README.md` | Folder overview page for this section of the documentation; see Related Pages. |
| `docs/release-notes/version-numbering.md` | Defines the MAJOR.MINOR.PATCH scheme referenced under "Version Numbering" above. |
| `docs/release-notes/changelog-conventions.md` | House style for changelog entries, applied to the worked example above. |
| `docs/release-notes/changelog-snippet-format.txt` | Exact formatting template the worked example follows. |
| `docs/release-notes/release-checklist.md` | The formal checklist; does not yet have a dedicated speed section as of this writing. |
| `docs/release-notes/release-checklist-template.yaml` | YAML template used when filling out a checklist for a given release. |
| `docs/release-notes/packaging-source-distribution.rst` | Packaging process; referenced under "Packaging and Speed" for the flat-directory and bytecode notes. |
| `docs/release-notes/build-environment-notes.rst` | Background on the flat-vs-nested packaging choice quoted above. |
| `docs/release-notes/command-help-text-changes.md` | Tracks help text changes; referenced to rule out help-text growth as a false speed complaint. |
| `docs/release-notes/console-log-format-changes.md` | Full account of console output format changes, several with speed motivations noted on this page. |
| `docs/release-notes/release-notes-v1.0.md` | Baseline release notes; no dedicated speed section. |
| `docs/release-notes/release-notes-v1.1.md` | First release notes page with a "Speed" section. |
| `docs/release-notes/release-notes-v1.2.md` | Release notes for the release with the largest recorded speed win on this page. |
| `scripts/` | Holds the informal timing snippet referenced above, kept as a loose shell script rather than a maintained tool. |

## Tools and Libraries Referenced

| Tool / Library | Version | Used for |
|---|---|---|
| Python (CPython) | 3.11.x on the reference laptop; package supports 3.9+ | Interpreter running the package; import surface and cold-start timing are interpreter-dependent. |
| SQLite (bundled with Python's standard library binding) | 3.42.x as bundled with Python 3.11 | Underlying engine for the database file; journal mode and synchronous setting behavior described above are SQLite-level settings. |
| `sqlite3` command-line tool | 3.42.x (matched to the bundled library where possible) | Manual maintenance operations such as the vacuum example above. |
| Bash | 5.x (via WSL on the reference laptop) | Running the timing loop snippet. |
| git | 2.43.x | Checking out release branches before timing runs. |
| Docs Guild changelog template | as defined in `changelog-snippet-format.txt` v1.0 | Format for changelog entries quoted on this page. |

## Change Log for This Page

- 2024-04-15 — Sam Okafor — Initial version of this page created, covering the v1.0.0 baseline figures only.
- 2024-09-10 — Mara Olsen — Added the v1.1.0 speed section, including the WAL journal mode change and the import surface reduction.
- 2025-02-25 — Sam Okafor — Added the v1.2.0 section covering the synchronous setting change and the connection-lifetime journal mode check.
- 2025-04-12 — Sam Okafor — Folded in the v1.2.1 console output flush interval revert, noting it has no standalone release notes page.
- 2025-08-06 — Priya Chandran — Added the informal vacuum threshold guidance for v1.3.0 and cross-referenced the release checklist gap.
- 2025-11-02 — Sam Okafor — Reworked the "Reading the Numbers on This Page" caution section, added the tools table, and drafted the in-progress v1.4.0 section ahead of the corresponding release notes page.

## Related Pages

- Release Notes Folder Overview
- Version Numbering for the Package
- Changelog Writing Conventions
- Changelog Snippet Format
- Release Checklist
- Release Checklist Template (YAML)
- Packaging the Source Distribution
- Build Environment Notes
- Command Help Text Changes Across Releases
- Console Log Format Changes Across Releases
- Release Notes: v1.0.0
- Release Notes: v1.1.0
- Release Notes: v1.2.0
