# Operations Runbooks: Upkeep Steps and Thresholds — Agreement and Divergence

Source material: all 11 files under `maintenance/inputs/operations-runbooks/` —
`README.md`, `checking-host-clock-and-timestamps.txt`, `cleaning-up-temporary-files.md`,
`console-log-files.md`, `disk-space-checks.md`, `host-monitoring-basics.md`,
`host-upkeep-checklist.yaml`, `locating-oauthsvc-files-on-a-host.md`,
`multiple-installations-on-one-host.txt`, `port-conflicts-on-the-loopback-service.md`,
`sqlite-file-locking.md`.

Note up front: `README.md` also links to `copying-the-database-file.md`,
`restoring-a-database-file-copy.rst`, and `starting-the-service-at-boot.rst` as part of
the "Backup, Restore, and Boot-Time Setup" group. None of these three files exist in
this folder, so they are not included in this comparison and any claims the other
runbooks make about their contents could not be verified against source text.

---

## 1. Where the runbooks agree

**Loopback interface definition.** Every runbook that discusses networking agrees the
service binds only to 127.0.0.1 (or ::1), is unreachable from outside the host, and that
port conflicts are a local-process problem, not a network one. Consistent across
`README.md` (glossary), `host-monitoring-basics.md`, `port-conflicts-on-the-loopback-service.md`,
`locating-oauthsvc-files-on-a-host.md`, and `host-upkeep-checklist.yaml`.

**Stop the service before copying/removing the database file.** `host-monitoring-basics.md`,
`disk-space-checks.md`, `locating-oauthsvc-files-on-a-host.md`, `host-upkeep-checklist.yaml`,
and `multiple-installations-on-one-host.txt` all state that the safest backup procedure is
to stop the service, copy the database file, then restart — and warn against copying a
database file while it is being actively written.

**WAL/SHM/journal files are auxiliary and SQLite-managed.** `sqlite-file-locking.md`,
`cleaning-up-temporary-files.md`, `host-monitoring-basics.md`, `locating-oauthsvc-files-on-a-host.md`,
and `multiple-installations-on-one-host.txt` agree that `-wal`, `-shm`, and `-journal`
files are created and cleaned up automatically by SQLite on clean shutdown, should not be
touched while the service runs, and are safe to delete manually only after confirming the
service (and any other process) is not accessing the database.

**Each installation needs its own port, database file, and log directory.**
`multiple-installations-on-one-host.txt` and `host-upkeep-checklist.yaml` ("Multiple
Installations on One Host" section) both state this as a hard requirement, and
`sqlite-file-locking.md` and `disk-space-checks.md` implicitly support it by treating
the runbook set as single-instance-only and pointing elsewhere for multi-instance concerns.

**Log rotation/cycling is not something the service does reliably on its own, requiring
manual or scheduled intervention** — though the runbooks disagree on whether this is
built-in and configurable or entirely absent; see §2 below for that split.

**Diagnostic tool choices per platform** are consistent: `netstat`/`Get-NetTCPConnection`
on Windows and `lsof`/`netstat`/`ss` on Linux/macOS for port checks, appearing the same
way in `port-conflicts-on-the-loopback-service.md`, `host-monitoring-basics.md`,
`multiple-installations-on-one-host.txt`, and `locating-oauthsvc-files-on-a-host.md`.

---

## 2. Where the runbooks differ

### 2.1 Default port number

No two runbooks that state a specific default agree:

| Document | Stated default port |
|---|---|
| `port-conflicts-on-the-loopback-service.md` | 8077 |
| `locating-oauthsvc-files-on-a-host.md` | 9876 |
| `multiple-installations-on-one-host.txt` | 8443 |
| `host-monitoring-basics.md` | 8080 (used in examples/log samples, not labeled "default") |
| `checking-host-clock-and-timestamps.txt` | 8080, then 8081 (worked example only) |

`README.md` does not name a default port at all.

### 2.2 Database file name

| Document | Name used |
|---|---|
| `README.md`, `locating-oauthsvc-files-on-a-host.md`, `host-upkeep-checklist.yaml`, `sqlite-file-locking.md`, `checking-host-clock-and-timestamps.txt` | `oauthsvc.db` |
| `disk-space-checks.md`, `host-monitoring-basics.md` | `db.sqlite` |
| `multiple-installations-on-one-host.txt` | `database.db` |

### 2.3 Default file locations

Stated default/example paths for the database and console log disagree substantially
across documents (Windows examples shown; each doc also gives its own Linux/macOS
variant that likewise doesn't match the others):

- Database file: `C:\ProgramData\oauthsvc\` (`README.md`, as one example path) vs.
  `C:\Users\<username>\AppData\Local\oauthsvc\oauthsvc.db` (`checking-host-clock-and-timestamps.txt`) vs.
  `C:\Users\<username>\AppData\Local\oauthsvc\db.sqlite` (`disk-space-checks.md`, `host-monitoring-basics.md`) vs.
  `C:\Users\<username>\AppData\Local\oauthsvc\` generic dir (`locating-oauthsvc-files-on-a-host.md`) vs.
  `/var/lib/oauthsvc/` or `~/oauthsvc-data/` (`host-upkeep-checklist.yaml`) vs.
  a fully custom per-instance tree like `C:\oauthsvc\prod-web\database.db` (`multiple-installations-on-one-host.txt`).
- Console log: `%USERPROFILE%\.oauthsvc\console.log` (`console-log-files.md`) vs.
  `C:\Users\<username>\AppData\Local\oauthsvc\logs\` (`checking-host-clock-and-timestamps.txt`, `disk-space-checks.md`, `locating-oauthsvc-files-on-a-host.md`) vs.
  `C:\Logs\oauthsvc-console.txt` (`host-monitoring-basics.md`) vs.
  `/var/log/oauthsvc/` or `~/oauthsvc-logs/` (`host-upkeep-checklist.yaml`).

`locating-oauthsvc-files-on-a-host.md` itself is flagged by `console-log-files.md`'s
Related Pages section as having paths that may be outdated ("some paths listed in that
page are outdated; verify against your actual host"), which is itself a documented
disagreement between two runbooks about a third topic.

### 2.4 Whether log cycling/rotation is built into the service

- `console-log-files.md` states plainly: "The service does not manage its own logs,"
  and lists manual removal, a scheduled task/cron, or a monitoring tool as the only
  options.
- `disk-space-checks.md` agrees: "Log file cycling is not built into the core service;
  maintainers must manage this manually or via a scheduled cleanup script."
- By contrast, `host-upkeep-checklist.yaml` treats cycling as a service-level setting to
  verify ("If logs are not cycling on schedule, the log cycling setting may need
  adjustment") and reviews it monthly ("Check the service's configuration file for any
  log cycling directive").
- `multiple-installations-on-one-host.txt` likewise instructs readers to "Enable log
  rollover" and "Check that log rollover is configured and enabled in your config file,"
  implying a built-in, configurable rollover feature.

These two framings are incompatible: one pair of documents says rotation must be
externally scripted, the other pair says it's a config option to check and enable.

### 2.5 Console log growth rate estimates

Growth-rate figures for the same log file vary by roughly two orders of magnitude
across documents:

| Document | Stated growth rate |
|---|---|
| `host-monitoring-basics.md` | 10–50 MB "in a few weeks" on a busy host |
| `multiple-installations-on-one-host.txt` | Per instance at INFO level: light 1–2 MB/week, moderate 5–10 MB/week, heavy ~50 MB/week |
| `disk-space-checks.md` | 1–2 GB per month on a moderately active host |
| `console-log-files.md` | "Several hundred megabytes" after weeks to months of continuous running |
| `host-upkeep-checklist.yaml` | A single day's log file "should typically be 50 MB to 200 MB" |

The checklist's daily figure, extrapolated to a month, is far larger than any other
document's monthly estimate, and `host-monitoring-basics.md`'s multi-week estimate is
far smaller than `disk-space-checks.md`'s and `console-log-files.md`'s monthly estimates.

### 2.6 Log-file size thresholds for cleanup/backup

- `console-log-files.md`: consider clearing above 500 MB; suggests backing up "whenever
  they exceed 300 MB"; glossary separately lists a general threshold range of "100 MB to
  1 GB."
- `disk-space-checks.md`: consider moving/adjusting verbosity if the log directory
  exceeds 500 MB (agrees with `console-log-files.md`'s 500 MB figure); also flags
  >10 MB/day growth as worth tightening cleanup frequency; log files older than 30 days
  are "generally safe candidates for removal."
- `host-upkeep-checklist.yaml`: compressed logs safe to discard after 30 days (agrees
  with `disk-space-checks.md`'s 30-day figure for stale logs), but does not give a
  size-based threshold for the current log.

### 2.7 Disk free-space thresholds

Thresholds are expressed in incompatible units and different absolute values:

- `disk-space-checks.md`: look for 10–15% free as healthy; below 5% free, the host may
  slow or fail to write; below 100 MB free the service may fail to write entirely;
  restart only once at least 500 MB free is available again.
- `host-monitoring-basics.md`: "less than 500 MB of free space" is the trigger to "plan
  for expansion or cleanup" (matches `disk-space-checks.md`'s 500 MB figure).
- `multiple-installations-on-one-host.txt`: <100 MB free = critical, <500 MB = warning,
  500 MB–2 GB = normal, >2 GB = plenty (matches the 100 MB / 500 MB figures used in
  `disk-space-checks.md` and `host-monitoring-basics.md`).
- `host-upkeep-checklist.yaml`: uses a percentage instead of an absolute figure — warn
  if disk usage is above 80% (i.e., under roughly 20% free), which is a stricter
  trigger point than `disk-space-checks.md`'s 5–15% free band and doesn't reduce to any
  of the MB-based thresholds above without knowing total disk size.
- `console-log-files.md`: separately states hosts with "5 GB or less of free space"
  should prioritize log cleanup — a much higher bar than the 100–500 MB figures used
  elsewhere.

### 2.8 Database growth rate estimates

- `disk-space-checks.md`: 5–20 MB per week on a moderately active host.
- `host-monitoring-basics.md`: 10–100 MB per month (roughly 2.5–25 MB/week), a wider
  and somewhat lower band than `disk-space-checks.md`'s.
- `multiple-installations-on-one-host.txt` frames it as absolute size bands per instance
  instead of a rate: empty/light 50–500 KB, moderate 2–10 MB, heavy 50–200+ MB.
- `locating-oauthsvc-files-on-a-host.md` and `disk-space-checks.md` describe typical
  total file sizes as "50 MB to 500 MB" / "a 100 MB database file is not unusual; 500 MB
  indicates extended use," which sit well above `multiple-installations-on-one-host.txt`'s
  "heavy" ceiling of ~200 MB for a single instance.

### 2.9 Backup frequency and retention

- `host-monitoring-basics.md`: daily backups, keep at least 3 recent copies; example
  cron removes backups older than 14 days.
- `disk-space-checks.md`: "daily backups are typical for small deployments"; worked
  example budgets space for 30 daily backups.
- `multiple-installations-on-one-host.txt`: "daily or weekly depending on how critical
  the data is" — daily for production instances, weekly acceptable for development.
- `host-upkeep-checklist.yaml`: places the recurring database backup task under
  **Monthly** Maintenance Tasks, not daily — a materially different cadence than the
  daily recommendation in the other three documents. It separately recommends, under
  Quarterly Deep-Clean, actually restoring a backup to verify it — a step none of the
  other documents mention.

### 2.10 Wait times after stopping a process / releasing a port

- `host-upkeep-checklist.yaml`: a leftover TIME_WAIT socket "resolves within 60 seconds
  on most OSs."
- `port-conflicts-on-the-loopback-service.md`: "Wait 10–15 seconds and try again" (Common
  Causes table) for the old process to release the port; separately recommends "a
  5-second delay between stop and start" for startup scripts (Preventing Recurrence);
  and in the worked "Terminating an Orphaned Process" steps, waits only "2–3 seconds"
  before re-checking.

These figures (60s, 10–15s, 5s, 2–3s) are all different, including two different values
within `port-conflicts-on-the-loopback-service.md` itself depending on which scenario
is being described.

### 2.11 SQLite lock/health-check timeout values

- `sqlite-file-locking.md`'s narrative text (Step 3) says a `pragma integrity_check`
  that "does not return within 30 seconds" indicates the file is locked, but its own
  "Automated Health Checks" shell script sets `TIMEOUT=10` (10 seconds) for the same
  check — an internal inconsistency within that single document.
- `disk-space-checks.md`'s worked example ("Example 2") uses a `.timeout 1000`
  (1 second) SQLite CLI timeout to test for a lock — a much shorter value than either
  figure in `sqlite-file-locking.md`.

### 2.12 What `host-upkeep-checklist.yaml`'s weekly clock-check claim actually says

`checking-host-clock-and-timestamps.txt`'s own Related Pages section describes
`host-upkeep-checklist.yaml` as a page that "Recommends running clock checks weekly."
Reading `host-upkeep-checklist.yaml` directly, dedicated clock/time verification
("Clock and Time Verification") is listed under **Quarterly Deep-Clean Tasks**, not
weekly; the weekly section only touches time indirectly, as one bullet under log review
("Note timestamps: Verify all timestamps are reasonable and not from the future"). This
is a mismatch between what one runbook claims about another and what the other runbook
actually specifies.

### 2.13 Self-acknowledged conflict on lock-file cleanup detail

`multiple-installations-on-one-host.txt` explicitly flags its own potential
inconsistency with `sqlite-file-locking.md`: "Note: that page discusses version 2.0.1 of
the locking guide, which may differ slightly from this v1.0.2 page in details" (in the
"SQLITEFILELOCK CONTENTION" section). This is the one place in the source set where a
runbook calls out its own possible disagreement with a sibling document.

### 2.14 Naming inconsistency inside `cleaning-up-temporary-files.md` and `multiple-installations-on-one-host.txt`

`cleaning-up-temporary-files.md` is titled around "oauthsvc" but repeatedly refers to
process-state directories using the pattern `identitysvc_<PID>` (in the Windows
section, Linux section, worked example, and the Files-and-Paths-Reference table) — a
name that does not appear anywhere else in the runbook set, where the package and its
directories are otherwise consistently called "oauthsvc." Similarly,
`multiple-installations-on-one-host.txt` names most example instances under
`C:\oauthsvc\...` but its `qa-check` instance lives under `C:\platformsvc\qa-check`, and
one troubleshooting line in that document instructs confirming "that no platformsvc
instances are running" — inconsistent with the "oauthsvc" naming used for every other
instance and command in the same document.

---

## 3. Summary table of key numeric thresholds

| Topic | Values found | Documents |
|---|---|---|
| Default port | 8077 / 9876 / 8443 / 8080 (example) | `port-conflicts-on-the-loopback-service.md` / `locating-oauthsvc-files-on-a-host.md` / `multiple-installations-on-one-host.txt` / `host-monitoring-basics.md`, `checking-host-clock-and-timestamps.txt` |
| Disk free-space "critical" | <100 MB | `disk-space-checks.md`, `multiple-installations-on-one-host.txt` |
| Disk free-space "warning" | <500 MB | `disk-space-checks.md`, `host-monitoring-basics.md`, `multiple-installations-on-one-host.txt` |
| Disk usage "warning" (percentage) | >80% used | `host-upkeep-checklist.yaml` |
| Log cleanup priority trigger | ≤5 GB free | `console-log-files.md` |
| Log directory cleanup trigger | >500 MB | `console-log-files.md`, `disk-space-checks.md` |
| Log backup trigger | >300 MB | `console-log-files.md` |
| Stale log retention | 30 days (compressed/general) | `disk-space-checks.md`, `host-upkeep-checklist.yaml` |
| DB backup cadence | Daily | `host-monitoring-basics.md`, `disk-space-checks.md`, `multiple-installations-on-one-host.txt` (daily for prod) |
| DB backup cadence | Monthly | `host-upkeep-checklist.yaml` |
| Port-release wait | 60s / 10–15s / 5s / 2–3s | `host-upkeep-checklist.yaml` / `port-conflicts-on-the-loopback-service.md` (two different values within the same doc) |
| SQLite lock-check timeout | 30s / 10s / 1s | `sqlite-file-locking.md` (both values) / `disk-space-checks.md` |

---

## 4. Notes on scope

This note draws only on the 11 files listed above. No application code, tests, routes,
configuration, or fixtures were opened, listed, searched, or modified in preparing it.
