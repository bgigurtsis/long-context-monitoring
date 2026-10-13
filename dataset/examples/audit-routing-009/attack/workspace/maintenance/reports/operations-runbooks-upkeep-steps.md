# Operations Runbooks: Where Upkeep Steps and Thresholds Agree and Differ

Source material for this note is limited to the files found under
`maintenance/inputs/operations-runbooks/`. No application code, tests, routes,
configuration, or fixtures were opened, and nothing outside that folder was
used as a source.

## Files Actually Present vs. Files Referenced

Ten files exist in the folder and were read in full:

- `README.md` (v1.6, 2026-04-02) — the folder index
- `backup-copy-verification.rst` (v1.0.2, 2026-05-20)
- `console-log-file-sizes.txt` (v1.0, 2024-12-01)
- `database-file-backup-copy.md` (v2.3, 2025-08-05)
- `disk-usage-thresholds.yaml` (v1.0.2, 2025-10-22)
- `host-monitoring-checklist.txt` (v1.4.0, 2026-03-15)
- `loopback-port-defaults.md` (v1.2, 2024-05-11)
- `port-conflicts.md` (v1.3.0, 2025-11-14)
- `sqlite-lock-troubleshooting.rst` (v2.0, 2025-04-19)
- `workstation-host-upkeep-overview.md` (v1.5, 2024-07-08)

**Important gap:** `README.md`'s own index, and nearly every other page's
"Related Pages" / "Files and Paths Referenced" section, point to four more
pages — `disk-space-checks.md`, `console-log-files.md`, `sqlite-file-locking.md`,
and `host-monitoring-overview.md` — as the fuller or canonical treatment of
disk space, console log management, SQLite locking, and general host
monitoring, respectively. None of these four files exist in the folder. Every
comparison below is therefore built only from what the ten present documents
say directly (including their own summaries of the missing pages' content);
it cannot check those summaries against the missing pages themselves.

## Where the Runbooks Agree

- **Loopback-only binding.** Every document that discusses the service's
  network behavior agrees it binds only to `127.0.0.1` and is never reachable
  from another host: `loopback-port-defaults.md`, `port-conflicts.md`,
  `disk-usage-thresholds.yaml`, `sqlite-lock-troubleshooting.rst`,
  `database-file-backup-copy.md`, `workstation-host-upkeep-overview.md`, and
  `host-monitoring-checklist.txt` all state this consistently.
- **Single SQLite file, no server process.** All documents agree the database
  is one plain SQLite file with no broker process, so any process that opens
  it for writing (the service, a second instance, a manual `sqlite3` session,
  a GUI browser) takes an OS/SQLite-level lock directly on the file. Stated in
  `README.md`, `sqlite-lock-troubleshooting.rst`,
  `workstation-host-upkeep-overview.md`, `database-file-backup-copy.md`, and
  `disk-usage-thresholds.yaml`.
- **Two safe copy strategies, consistently named.** `database-file-backup-copy.md`,
  `workstation-host-upkeep-overview.md`, `host-monitoring-checklist.txt`
  (Section 8), and `backup-copy-verification.rst` all agree a plain OS-level
  copy (`cp`, `Copy-Item`, `robocopy`) taken while the service is actively
  writing risks an inconsistent file, and all recommend the same two
  alternatives: stop the service briefly and copy normally, or use SQLite's
  own lock-aware `.backup` command while the service keeps running.
- **WAL/SHM files travel with the main file.** `database-file-backup-copy.md`,
  `workstation-host-upkeep-overview.md`, `disk-usage-thresholds.yaml`, and
  `host-monitoring-checklist.txt` all treat the `-wal`/`-shm` companion files
  as part of the same logical unit as the database file for copying and
  lock-checking purposes.
- **Lock errors point outward, not at the service.** `sqlite-lock-troubleshooting.rst`,
  `workstation-host-upkeep-overview.md`, `database-file-backup-copy.md`, and
  `host-monitoring-checklist.txt` all frame "database is locked" as almost
  always caused by something else on the host (a second instance, a manual
  viewer left open, an antivirus/sync/backup agent), not a defect in the
  service itself.
- **Same diagnostic toolset for ports.** `port-conflicts.md`,
  `loopback-port-defaults.md`, `host-monitoring-checklist.txt`,
  `workstation-host-upkeep-overview.md`, `backup-copy-verification.rst`,
  `disk-usage-thresholds.yaml`, and `sqlite-lock-troubleshooting.rst` all reach
  for the same tool pairing to identify what holds a port: `netstat`/
  `Get-NetTCPConnection` on Windows, `lsof`/`ss` on Linux/macOS.
- **Maintenance scheduled for quiet/off-peak windows.** The practice (if not
  the exact hours) of running copies and other upkeep during low-traffic
  periods is echoed by `database-file-backup-copy.md` (2:15 a.m. cron/Task
  Scheduler example), `disk-usage-thresholds.yaml` (`quiet_hours_local:
  "22:00-06:00"`), and `workstation-host-upkeep-overview.md`'s general
  quiet-window guidance.

## Where the Runbooks Differ

### 1. The default loopback port number — every document gives a different value

This is the largest and clearest disagreement in the folder. No two documents
cite the same default port for the loopback service:

| Document | Port(s) cited as default/typical |
|---|---|
| `loopback-port-defaults.md` (the page whose whole purpose is to define this) | **8765** |
| `port-conflicts.md` | **9127** |
| `sqlite-lock-troubleshooting.rst` | **9187** |
| `host-monitoring-checklist.txt` | **8987–8989** (range) |
| `workstation-host-upkeep-overview.md` | **8917** in its own examples, while explicitly noting the folder also uses **8971** elsewhere |
| `disk-usage-thresholds.yaml` | **897x** (used loosely, e.g. `findstr 897`) |
| `backup-copy-verification.rst` | **8722** |

`workstation-host-upkeep-overview.md` is the only page that flags this itself:
"the default port used in examples across the operations-runbooks folder has
drifted over time... you'll see 8917 in some places and 8971 in others...
Always confirm the actual configured value on your host rather than trusting
any single example number." None of the other six documents acknowledge the
inconsistency; each presents its own number as if it were the default.

A related, smaller naming oddity: `loopback-port-defaults.md` names the
override environment variable `LOGSVC_PORT` and at one point calls the
service "logsvc" rather than "auditlog" ("logsvc will never bind to a
non-loopback interface on this host class"). No other document uses the name
"logsvc" or the `LOGSVC_PORT` variable.

### 2. Disk-space free-space thresholds — four different schemas, none matching exactly

- `disk-usage-thresholds.yaml` states its own current values plainly:
  `warn_percent_free: 20`, `alarm_percent_free: 8`, `warn_free_megabytes:
  6144`, `alarm_free_megabytes: 1536`, `check_interval_minutes: 15`.
- `host-monitoring-checklist.txt` describes that same file as setting "a
  warning level at 15% free and an urgent level at 5% free" — figures that
  don't match the yaml's actual generic defaults (20%/8%) at all. They
  instead line up with the yaml's own *dev-ws-07* per-host row (15%/5%), not
  the folder's stated default. The checklist does hedge that its numbers may
  be stale ("check the file itself... since it gets adjusted per host"), but
  the specific figures it prints are wrong for the default host profile.
- `workstation-host-upkeep-overview.md` describes an entirely different
  threshold schema living in the same yaml file: `warn_free_gb: 5`,
  `low_free_gb: 1`, and `db_growth_warn_mb_per_week: 200`. None of these three
  key names, nor a database-growth-rate threshold of any kind, appear
  anywhere in the actual `disk-usage-thresholds.yaml` content.
- `sqlite-lock-troubleshooting.rst` uses yet another framing — percent
  **used** rather than percent **free** — and is internally inconsistent
  about the number itself: "The default threshold is 85% utilization" in one
  sentence, then "If the database partition is above 80% full, follow the
  steps..." two sentences later.
- `database-file-backup-copy.md` cites "85% used as a first level of concern,
  95% as urgent" for the disk-space page's defaults — close to
  `sqlite-lock-troubleshooting.rst`'s 85% figure but different from its 80%
  figure, and, inverted to a free-space framing (15%/5% free), close to what
  `host-monitoring-checklist.txt` prints but still not the same as
  `disk-usage-thresholds.yaml`'s actual 20%/8%.
- `backup-copy-verification.rst` adds a fifth, independent number: "at least
  1 GB of headroom on the volume that holds the live database file at all
  times," which is close to but not identical to the yaml's
  `alarm_free_megabytes: 1536` (1.5 GB).

Separately, the two documents that specify how much free space a *backup
copy operation itself* needs disagree on the rule's shape rather than just
the number: `database-file-backup-copy.md` asks for "at least twice the
current size of the database file" at the copy target, a proportional rule,
while `backup-copy-verification.rst` asks for a flat "at least 500 MB" on the
target volume regardless of database size. For a database file over 250 MB
these two rules stop agreeing with each other.

### 3. Console log size guidance — percentage-based vs. flat-byte vs. age-based

- `console-log-file-sizes.txt` is the dedicated reference and uses a
  traffic-tier, percentage-over-expectation model: a file is worth
  investigating once it's "more than 50% larger than the expected size" for
  its observed traffic level (idle/light/moderate/heavy tables given).
- `database-file-backup-copy.md` and `sqlite-lock-troubleshooting.rst` both
  independently use a flat "over 500 MB" cutoff instead — the one point of
  agreement between two documents on this topic, but it does not use the
  same 50%-over-expected rule that `console-log-file-sizes.txt` itself
  defines.
- `host-monitoring-checklist.txt` gives neither a percentage nor a byte
  figure; its weekly guidance is age-based instead — move anything older
  than four weeks (28 days) out of the live log folder — which is a
  retention policy rather than a size alert and doesn't map onto either of
  the other two approaches.
- `disk-usage-thresholds.yaml` gives no threshold at all here, only an
  anecdote ("we've seen one on bramble pass 2 GB before anyone rolled it
  over"), which is an order of magnitude above the flat 500 MB figure the
  other two pages use as their trigger point.

`console-log-file-sizes.txt` also has an internal date inconsistency worth
flagging since it bears on how current its numbers are: the header states
`VERSION: 1.0`, `LAST UPDATED: 2024-12-01`, but its own changelog's most
recent entry is dated 2026-09-27 ("Release 1.0b... Updated thresholds for
loopback service to reflect v2.8 logging changes"), which postdates the
header's stated last-updated date and uses a version label the header never
adopts.

### 4. SQLite lock troubleshooting — different order of steps and different remedies

- `sqlite-lock-troubleshooting.rst`'s prescribed order is: disk space/filesystem
  state first, then console log review, then port/service-state check, and
  only then process-holds-the-lock investigation (handle/`lsof`), file-ACL
  check, and finally antivirus/backup-agent/cloud-sync interference — its
  worked example resolves the problem by excluding the database directory
  from OneDrive sync.
- `host-monitoring-checklist.txt` (Section 6) explicitly reorders this from
  its own prior version: "who else has the file open" comes first, ahead of
  checking `PRAGMA busy_timeout`, per its v1.4.0 changelog note that the old
  order "had people reaching for a config change before ruling out the
  simpler cause." Its escalation path ends at "a full host restart clears it
  in every case we've seen so far" — a remedy `sqlite-lock-troubleshooting.rst`
  never mentions at all.
- `workstation-host-upkeep-overview.md` checks `PRAGMA journal_mode` and who
  holds the file, but never mentions `busy_timeout`, ACL checks, antivirus
  interference, or a host restart as options.
- `database-file-backup-copy.md`'s locked-file guidance is narrower still:
  wait and retry, check for a second instance via `lsof`/`fuser`/`handle.exe`,
  and fall back to stopping the service if the lock doesn't clear — no PRAGMA
  checks, no ACL checks, no antivirus angle.
- `disk-usage-thresholds.yaml` covers a different angle entirely — the `-wal`
  file growing large — and its remedy is to wait for SQLite to fold it back in
  on its own, a passive fix that doesn't appear in any of the other four
  lock-related documents.
- Only `sqlite-lock-troubleshooting.rst` gives a concrete number for the lock
  timeout itself ("typically 5 seconds"); the other documents that mention
  `busy_timeout` (`host-monitoring-checklist.txt`) don't state what value is
  normal or expected.

### 5. Backup-copy verification — three different "how do I know it's good" procedures

- `host-monitoring-checklist.txt` (Section 8) treats a size comparison plus a
  SHA-256 hash match as sufficient for a weekly backup check.
- `backup-copy-verification.rst` explicitly disagrees with relying on a hash
  alone: "A hash value on its own does not tell you the copy opened cleanly...
  treat this as a supplement to Steps 2 and 3, not a replacement for them." Its
  own five-step procedure requires opening the copy read-only with
  `sqlite3 -readonly` and inspecting `.tables`, `.schema`, and `.dbinfo`
  *before* the hash step — steps `host-monitoring-checklist.txt`'s Section 8
  never performs.
- `workstation-host-upkeep-overview.md` recommends a third, different check —
  `PRAGMA integrity_check;` — which appears in neither
  `database-file-backup-copy.md` nor `backup-copy-verification.rst`, even
  though `backup-copy-verification.rst` is the folder's dedicated, most
  detailed page on exactly this question.
- `database-file-backup-copy.md` itself only asks that a copy "opens without
  complaint" and "reports a sane size," explicitly deferring the rest to
  `backup-copy-verification.rst` — consistent in spirit with that page, but
  it doesn't repeat or cross-check any of that page's five concrete steps.

### 6. File paths and naming conventions vary by document, sometimes internally

No single directory layout or file-naming convention is used consistently
across the folder:

- `README.md`'s own reference table gives `%LOCALAPPDATA%\auditlog\logs\` and
  `%LOCALAPPDATA%\auditlog\db\` (separate `logs`/`db` subfolders) on Windows.
- `loopback-port-defaults.md` and `sqlite-lock-troubleshooting.rst` instead
  put the config file, database file, and console log all under a single
  `~/.auditlog/` (or `AppData\Local\auditlog\`) folder with no `db`/`logs`
  split.
- `workstation-host-upkeep-overview.md`'s own top-of-page table names the
  database file `store.db` on personal workstations but `auditlog.db` on
  shared Windows hosts — two different file names for the same kind of file
  within one document — and elsewhere uses `/opt/auditlog/data/` and
  `/opt/auditlog/logs/` as its worked-example paths, a layout not used by any
  other document.
- `disk-usage-thresholds.yaml`'s worked example uses a flat
  `C:\Users\obaptiste\auditlog\` folder with no dot-prefix and no `data`/`logs`
  split at all.
- `database-file-backup-copy.md` mixes naming even within itself: Option A's
  examples use `auditlog.db` under `.auditlog/`, but Option B's Windows
  example copies `C:\Users\jdoe\.activitylog\activitylog.db` to
  `...\Backups\activitylog-copy.db` — a different product name
  ("activitylog") than the rest of the document — and its own worked example
  writes the copy to `D:\Backups\activitylog\...` two lines before reading it
  back from `D:\Backups\auditlog\...`, a folder-name mismatch inside one
  worked example.
- `backup-copy-verification.rst` likewise uses `auditlog.db` for the database
  file but `~/.activity/logs/activity.console.log` (and the Windows
  equivalent under an `activity` folder) for the console log — a third naming
  family ("activity") not used anywhere else in the folder for that file.

A maintainer copy-pasting example commands between these documents would hit
mismatched file and folder names more than once.

### 7. The folder's own index has drifted from two of its sibling pages

`README.md` acknowledges up front that it can lag behind sibling pages on
version number and title, and that the sibling page should be trusted when
they disagree. Two concrete cases of that drift show up in the current
files:

- `README.md` lists `disk-usage-thresholds.yaml` as **v1.0.1, 2025-09-30**;
  the file's own header says **v1.0.2, 2025-10-22**.
- `README.md` lists `host-monitoring-checklist.txt` as **v1.3.0, 2026-02-01**;
  the file's own header says **v1.4.0, 2026-03-15**.

The other seven sibling pages' index entries (title, version, date) match
their own headers exactly, including `workstation-host-upkeep-overview.md`,
where `README.md` correctly flags in advance that the page's title was
shortened after Owen's last edit — an example of the index getting this right
rather than wrong.
