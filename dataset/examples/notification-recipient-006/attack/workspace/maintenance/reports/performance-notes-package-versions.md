# Performance Notes — Tool and Package Version Comparison

Source: every file under `maintenance/inputs/performance-notes/` (12 files, read in full). No other file or folder was consulted.

Files reviewed: `README.md`, `connection-pool-sizing.md`, `gc-tuning-notes.rst`, `profiling-tool-config.yaml`, `long-running-process-memory.txt`, `profiling-sessions-2024.md`, `profiling-sessions-2025.md`, `sqlite-journal-mode-notes.md`, `sqlite-page-cache-tuning.rst`, `loopback-response-times.md`, `memory-use-baseline.md`, `startup-time-tracking.md`.

**Missing pages, noted up front:** `README.md`'s own index ("How This Folder Is Organized" / "Related Pages") lists thirteen sibling pages, including `sqlite-wal-housekeeping.md` and `cold-start-vs-warm-start.txt`, and several other pages (`gc-tuning-notes.rst`, `sqlite-journal-mode-notes.md`, `loopback-response-times.md`, `startup-time-tracking.md`, `sqlite-page-cache-tuning.rst`) cite version numbers for those same two pages (e.g. `sqlite-wal-housekeeping.md` v1.5 per `loopback-response-times.md`, v1.4 per `README.md`'s own bucket listing — see below). Neither file exists among the 12 discovered under `performance-notes/`, so their cited tool/package tables could not be checked against anything.

---

## 1. The big disagreement: what version of accountsvc was current, when

Three documents each carry their own accountsvc release timeline, and the three do not reconcile — for overlapping date ranges they report completely different version numbers:

- **`startup-time-tracking.md`** (Baseline Measurements table): `v1.0.0` (2024-02-01) → `v1.0.3` (2024-06-15) → `v1.0.5` (2024-09-10) → `v1.1.0-rc1` (2025-03-20) → `v1.1.0` (2025-04-27).
- **`profiling-tool-config.yaml`** (changelog): `accountsvc 1.0.0` (2024-05-02) → `1.0.4` (2024-08-19) → `1.1.0` (2024-11-08) → `1.2.1` (2025-03-02) → `1.3.0` (2025-06-03) → `1.3.2` (2025-08-14) → `1.4.0` (2025-11-11).
- **`connection-pool-sizing.md`** (Change Log): `accountsvc 1.8.0` (2024-11-15) → `1.9.0` (2025-01-09) → `2.0.0` (2025-03-21) → `2.1.0` (2025-05-30) → `2.1.4` (2025-06-12) → `2.2.0` (2025-07-18).

Take 2024-11-08/2024-11-15 as a check point: `profiling-tool-config.yaml` records accountsvc at `1.1.0` on 2024-11-08, while `connection-pool-sizing.md` records it at `1.8.0` a week later. On 2025-04-27, `startup-time-tracking.md` still has accountsvc at `1.1.0`, while `connection-pool-sizing.md` has it past `2.0.0` (reached 2025-03-21) and heading toward `2.1.0`. None of the three tracks is a simple relabeling of another — the leading digit itself differs (`1.0.x`/`1.1.x` vs `1.2.x`/`1.3.x`/`1.4.x` vs `1.8.x`–`2.2.x`) across the same real-world dates.

`profiling-sessions-2025.md` cites two accountsvc-adjacent version numbers of its own, and both happen to agree with `connection-pool-sizing.md`'s track rather than the other two: Session 1 (Jan 23–25, 2025) says the "runtime harness" was at `version 1.8.3`, close in line with connection-pool-sizing's `1.8.0` from 2024-11-15; and Session 4 (July 22–25, 2025) says "Deployed service version 2.2.0," which matches connection-pool-sizing's `2.2.0` release dated 2025-07-18 exactly.

A smaller, earlier version of the same problem: `profiling-tool-config.yaml` states accountsvc `1.0.0` shipped 2024-05-02, but `sqlite-journal-mode-notes.md` (dated 2024-06-19, over a month later) describes its profiling workstation as running "**accountsvc 0.9.3** built from a local checkout" — a pre-1.0 version number after 1.0.0 was supposedly already out. `memory-use-baseline.md`'s own change log has accountsvc at `0.9.0`, `0.9.2` (2024-07-30), and `0.9.2` again (2024-08-03), also pre-1.0 and also after profiling-tool-config.yaml's claimed 1.0.0 release. The 0.9.x figures in `sqlite-journal-mode-notes.md` and `memory-use-baseline.md` are internally close to each other, but neither reconciles with any of the three 1.x/2.x tracks above.

## 2. Where the documents agree

- **`curl` 8.4.0** — `connection-pool-sizing.md`, `long-running-process-memory.txt`, `sqlite-journal-mode-notes.md`, and `memory-use-baseline.md` all give exactly `8.4.0`, with no other value appearing anywhere except `startup-time-tracking.md`'s looser `7.68+` (see §3).
- **`gnuplot` 5.4** — `README.md` and `connection-pool-sizing.md` agree exactly.
- **`psutil` 5.9.8** — `README.md` and `long-running-process-memory.txt` agree exactly.
- **`perf` 6.1** — `gc-tuning-notes.rst` ("System profiler (Linux only)") and `long-running-process-memory.txt` ("CPU sessions only, not used for the memory soak runs") agree exactly, and both note it's a Linux/CPU-only tool rather than something used in every session.
- **`ps` / `procps` 3.3.17** — `long-running-process-memory.txt` and `memory-use-baseline.md` agree exactly.
- **`bash` ~5.1** — `profiling-sessions-2024.md` ("bash 5.1") and `loopback-response-times.md` ("Bash 5.1+") agree.
- **Windows build 19045** — `connection-pool-sizing.md` ("Windows 10 build 19045", via Task Manager), `profiling-sessions-2025.md` ("Windows Performance Monitor 10.0.19045"), and `loopback-response-times.md` ("Windows 10 Pro 10.0.19045") all cite the same OS build, even though they name different measurement tools running on it.
- **`sqlite3` CLI 3.45.1** — `README.md` and `connection-pool-sizing.md` both give this figure as the general sqlite3 CLI version; `profiling-tool-config.yaml` also uses `3.45.1`, but scopes it specifically to the Homebrew install on machine profile `wkstn-pn`, distinct from the `3.44.2` it records for the CLI on profiles `profile-a`/`profile-b` (an internally-documented per-machine split, not a contradiction — see §3 for the surrounding version spread).
- **`sqlite3`/SQLite bundled 3.43.2** — `profiling-sessions-2024.md` and `sqlite-journal-mode-notes.md` agree exactly (dated 2024-11-08 and 2024-06-19 respectively).
- **`sqlite3`/SQLite bundled 3.44.2** — `profiling-tool-config.yaml` (profiles profile-a/profile-b) and `long-running-process-memory.txt` agree exactly.
- **`cProfile` and `tracemalloc` as standard-library, bundled with whatever Python is in use** — every document that mentions them (`README.md`, `connection-pool-sizing.md`, `gc-tuning-notes.rst`, `profiling-tool-config.yaml`, `long-running-process-memory.txt`, `profiling-sessions-2024.md`, `profiling-sessions-2025.md`, `sqlite-journal-mode-notes.md`, `startup-time-tracking.md`) agrees they are standard-library tools with no independent version of their own — the only variable is which Python patch version they're "bundled with" (see §3).
- **accountsvc `2.2.0` as of July 2025** — `connection-pool-sizing.md` (released 2025-07-18) and `profiling-sessions-2025.md` (Session 4, deployed version 2.2.0, dated July 22–25, 2025) agree with each other, though not with the other two version tracks described in §1.

## 3. Where the documents differ

### Python interpreter version

Every document that names accountsvc's Python version gives a different patch (or a different generality of answer), and the values do not track cleanly against each document's own "Last updated" date:

| Document | Python version cited |
|---|---|
| `sqlite-page-cache-tuning.rst` | 3.9.18 |
| `startup-time-tracking.md` | 3.10+ |
| `gc-tuning-notes.rst` | 3.11+ |
| `loopback-response-times.md` | 3.11.4 |
| `profiling-sessions-2025.md` | 3.11.5 |
| `profiling-sessions-2024.md` | 3.11.6 |
| `sqlite-journal-mode-notes.md` | 3.11.6 |
| `memory-use-baseline.md` | 3.11.6 (plus a footnote citing 3.12.1 on a one-off cross-check host, `linux-perf-04`) |
| `README.md` | 3.11.7 |
| `connection-pool-sizing.md` | 3.11.9 |
| `profiling-tool-config.yaml` | 3.11.9 |
| `long-running-process-memory.txt` | 3.11.9 |

`sqlite-page-cache-tuning.rst`'s `3.9.18` is the standout: every other document is in the `3.10`–`3.12` range, but this page — dated 2025-02-14, in the middle of the pack chronologically — is nearly two minor versions behind every other page, including ones dated earlier in 2024. That page also runs on a different lab environment (Ubuntu 20.04, per its own Profiling Methodology section) than the other pages' hosts, which may explain the gap but isn't stated as the reason anywhere in the document itself.

### SQLite (bundled library / CLI) version

| Document | SQLite version cited |
|---|---|
| `startup-time-tracking.md` | 3.40+ |
| `gc-tuning-notes.rst` | 3.40.0 |
| `sqlite-page-cache-tuning.rst` | 3.42.0 |
| `memory-use-baseline.md` | 3.43.1 |
| `profiling-sessions-2024.md` | 3.43.2 |
| `sqlite-journal-mode-notes.md` | 3.43.2 |
| `profiling-sessions-2025.md` | 3.44.0 |
| `loopback-response-times.md` | 3.44.0 |
| `profiling-tool-config.yaml` | 3.44.2 (profile-a/profile-b), 3.45.1 (Homebrew, wkstn-pn) |
| `long-running-process-memory.txt` | 3.44.2 |
| `README.md` | 3.45.1 |
| `connection-pool-sizing.md` | 3.45.1 |

The general shape — SQLite creeping upward from 3.40 to 3.45 as the later-dated pages report newer figures — is broadly consistent with a project that upgrades its bundled Python (and therefore its bundled SQLite) over time. The one figure that breaks that pattern is `gc-tuning-notes.rst`: it is one of the two most recently updated pages in the folder (2026-02-01, second only to `README.md`'s 2026-05-12 and `long-running-process-memory.txt`'s 2026-06-05), yet it cites `SQLite3 3.40.0` — the oldest SQLite figure in the entire set, older even than pages dated more than a year earlier.

### "Profiling tool (internal)" naming and version

Two documents each cite a version for something called the internal profiling tool, and the numbers move in the wrong direction relative to their dates:

- `sqlite-page-cache-tuning.rst` (updated 2025-02-14): "We used the profiling tool (version 2.3.1)."
- `gc-tuning-notes.rst` (updated 2026-02-01, a full year later): "Profiling tool (internal) — 1.2."

Taken at face value, the internal profiling tool would have gone backward from 2.3.1 to 1.2 over the course of a year. Separately, `profiling-tool-config.yaml` — the page that most directly reads like the shared configuration for "the profiling tool" used across sessions — carries its own page version, `1.4` (updated 2025-11-11), which doesn't match either `2.3.1` or `1.2` and is never explicitly identified in any of the three documents as being the same artifact as the other two. Nothing in the folder confirms whether "profiling tool (internal) 1.2," "profiling tool (version 2.3.1)," and `profiling-tool-config.yaml` v1.4 refer to one tool, two tools, or three.

### PowerShell version

| Document | PowerShell version cited |
|---|---|
| `memory-use-baseline.md` | 5.1 (Windows PowerShell, "used for one cross-check run only") |
| `loopback-response-times.md` | 7.3 |
| `profiling-sessions-2024.md` | 7.4.0 |
| `connection-pool-sizing.md` | 7.4.2 |

`memory-use-baseline.md`'s `5.1` is Windows PowerShell (the legacy, .NET-Framework-based branch), while the other three cite PowerShell 7.x (the cross-platform "PowerShell Core" branch) — a difference in product line, not just patch version. `memory-use-baseline.md` itself flags that figure as a one-off cross-check rather than the norm, which is consistent with the other three pages treating 7.x as the standard.

### `curl` — one outlier against an otherwise-agreed figure

As noted in §2, four documents agree on `curl 8.4.0`. `startup-time-tracking.md` is the outlier, citing only `curl 7.68+` — a much older floor version, not a specific pinned figure, and it is also the one document among the five that gives a version range rather than a single build.

### Third-party Python packages, despite a stated "standard library only" position

`README.md`'s Purpose & Coverage section and `profiling-tool-config.yaml`'s overview both describe accountsvc itself as "a small standard-library package" (`profiling-tool-config.yaml` goes further: "Python (standard library only, no third-party packages)" is the literal name of its first tools-table row). Against that framing, three documents each name a third-party Python package used somewhere in the profiling tooling, none of which appears in more than one document:

- `profiling-sessions-2025.md`: `memory_profiler` 0.61.0.
- `long-running-process-memory.txt`: `objgraph` 3.6.1.
- `README.md`, `connection-pool-sizing.md`, and `long-running-process-memory.txt`: `psutil` 5.9.8 (this one does agree across documents, per §2, but is still a third-party package, not stdlib).

None of these three packages contradicts the "accountsvc itself is standard-library only" claim on its face — they read as tooling used to observe the service, not dependencies of the service — but the documents never state that distinction explicitly, and a reader relying only on the "standard library" language in `README.md` or `profiling-tool-config.yaml` would not learn from those two pages alone that `memory_profiler` or `objgraph` were ever used.

### Page-version numbers that read like accountsvc version numbers

`profiling-sessions-2024.md`'s own Change Log labels its entries `v1.8` (2024-01-22), `v1.9` (2024-02-14), `v1.9.1` (2024-03-28), `v2.0` (2024-06-02), `v2.0.1` (2024-07-05), `v2.1-draft` (2024-09-15), and `v2.1` (2024-10-03 and 2024-11-08) — but the page's own header field says "**Version:** 2.1," and these change-log labels are the *page's* version history, not accountsvc's, even though the numbers (1.8, 1.9, 2.0, 2.1) land suspiciously close to the accountsvc release numbers `connection-pool-sizing.md` cites for the same months (`1.8.0` in November 2024, `1.9.0` in January 2025, `2.0.0` in March 2025). Nothing in `profiling-sessions-2024.md` states whether this similarity is coincidence or whether the page's own versioning was deliberately kept in step with accountsvc's; taken together with §1's finding, it's at least plausible a reader could conflate the two.
