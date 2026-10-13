============================================
Verifying a Copied Database File
============================================

:Version: v1.0.2
:Owner: Platform Tools (Mara Olsen)
:Last updated: 2026-05-20
:Summary: Shows how a maintainer can confirm that a copy of the database file made for backup opened cleanly before relying on it.

Overview
========

*Section owner: Platform Tools (Mara Olsen)*

This page is the second half of the backup story for ``auditlog``. The
sibling page, *Copying the Database File for Backup*, walks through how
to make the copy in the first place — when to take it, which tool to use
on which operating system, and how to avoid disturbing the service while
it runs. This page assumes the copy already exists somewhere on disk and
answers the narrower question: **did the copy actually open cleanly, or
did you just move a pile of bytes from one folder to another?**

A copy that fails to open is worse than no copy at all, because it gives
a false sense of coverage. A maintainer who checked a shelf and found a
box there does not necessarily have anything usable inside the box. The
steps below give you a short, repeatable way to look inside the box
before you write the copy down as "done" for the day.

This runbook applies to both of the host shapes the team supports:

* a developer workstation running the package locally against a small
  database file under a home directory, and
* a small always-on host (a shared box in a closet, a low-spec cloud
  instance, or similar) running the loopback service continuously.

The verification steps are the same on both; only the paths and the
level of urgency differ.

Why Verification Matters
=========================

*Section owner: Platform Tools (Mara Olsen)*

A copy of a SQLite-backed database file can look correct and still be
unusable for a handful of reasons that are easy to overlook:

1. The copy was started while the source file had an open write, so the
   bytes on disk do not represent a single consistent moment.
2. The copy tool truncated the file because the target folder ran out
   of free space partway through.
3. A companion file next to the database file (a journal file left over
   from an interrupted write) was not copied along with it, so the main
   file alone tells an incomplete story.
4. The copy was made to a network share or removable drive that
   silently changed line endings, file modes, or file attributes in a,
   way that affects how local tools open it.
5. The copy is simply an older file than the maintainer thinks, because
   a folder alias or shortcut pointed somewhere unexpected.

None of these show up by looking at file size alone, and most of them
do not show up by looking at the modification date either. Opening the
copy and asking it a few basic questions is the only way to be
reasonably sure it is sound.

Before You Copy: Host Conditions to Check
==========================================

Verification starts before the copy is even made. If the host is in a
bad state — no free space, a stuck lock, a port fight between two
services, or a console log file quietly filling the disk — the copy you
make will inherit those problems, and the failure will only show up
later when you try to open it. The following four checks take a couple
of minutes combined and should be part of the same sitting as the copy
itself.

Disk Space
----------

*Section owner: Systems Engineering (Owen Baptiste)*

Before copying, confirm there is enough free space on the target volume
for a full copy of the database file plus a comfortable margin. As a
working rule, the team asks for at least 500 MB of free space on the
target volume before starting a copy of a typical workstation-sized
database file, and more on a small host where the file has had months
to grow.

On Linux or macOS::

    df -h /var/backups

On Windows (PowerShell)::

    Get-PSDrive -Name D | Select-Object Used,Free

If the source and target volumes are the same physical disk, remember
that the free-space number needs to cover the copy *in addition to* the
existing database file, not instead of it. A common mistake is reading
the free-space number, seeing it is larger than the database file, and
assuming that is sufficient — without accounting for the console log
files and any other copies already sitting in the same backup folder.

See *Checking Disk Space Around the Database File* for the full
threshold table and how the numbers were chosen; that page currently
recommends keeping at least 1 GB of headroom on the volume that holds
the live database file at all times, separate from whatever margin you
use for the backup folder itself.

Port Conflicts on the Loopback Service
---------------------------------------

*Section owner: Infra Reliability (Dez Whitfield)*

Port conflicts do not usually stop a file copy directly, but they matter
during verification whenever the check involves starting a second,
temporary instance of the loopback service pointed at the copy (some
maintainers prefer this over the command-line-only check described
below, because it exercises the same startup path the service uses
normally). If the loopback port the service listens on locally is
already taken — by the running production instance, by a leftover
process from an earlier session, or by an unrelated program that grabbed
the same local port — the second instance will not start, and a
maintainer might mistake "the service would not start" for "the copy is
bad."

Check what is listening on the local loopback port before you start a
verification instance:

On Linux::

    ss -ltnp | grep 127.0.0.1:8722

On Windows (PowerShell)::

    Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8722 |
        Select-Object State,OwningProcess

If the port is occupied by the instance you intend to keep running, use
a different local port for the verification instance rather than
stopping the running one. See *Diagnosing Port Conflicts for the
Loopback Service* and *Default Loopback Port Numbers and How to Change
Them* for how to pick and set a temporary port safely.

SQLite File Locking
--------------------

*Section owner: Platform Tools (Ines Carrow)*

SQLite uses file locks on the database file (and on its companion
journal file, when one is present) to keep concurrent access orderly.
Two things matter here for backup work:

- **Copying while a lock is held.** If you copy the database file with
  a plain file-copy tool while a write lock is held by the running
  service, most operating systems will still let the copy proceed, but
  the bytes you get may reflect a moment in the middle of a write. This
  is the single most common cause of a copy that will not open cleanly.
- **Locks on the copy itself.** Once you have a copy, opening it with a
  second tool while a first tool still has it open can produce a lock
  wait or a lock error that has nothing to do with the copy's own
  soundness — it is a locking condition on your own workstation, not a
  problem with the file.

To avoid the first case, either use the copy method described in
*Copying the Database File for Backup* (which briefly quiesces writes
before copying) or copy at a moment when the service is idle and has no
outstanding writes, which you can usually infer from a lull in the
console log file.

To avoid the second case, always close one verification tool fully
before opening the copy with another, and never point two verification
tools at the same copy path at the same moment.

See *Handling SQLite File Locking on the Database File* for the deeper
mechanics, and *Troubleshooting SQLite Lock Errors* if a lock condition
shows up mid-verification and does not clear after closing the
offending tool.

Console Log Files
------------------

*Section owner: Developer Experience (Priya Chandrasekaran)*

The service writes its own console log file next to (or in a
subdirectory alongside) the database file — on a workstation this is
often a rolling text file such as ``activity.console.log``, and on a
small host it may be forwarded there by whatever process manager keeps
the service running. This file is useful in verification for two
reasons:

1. If you copy the database file while the service is mid-write, the
   console log file will usually show the write starting close to the
   copy's timestamp, which is a hint (not proof) that the copy may have
   caught the file in an inconsistent moment.
2. After you open the copy with a check tool, briefly opening or
   starting a verification instance of the service against the copy
   will produce its own console log lines. Look at those lines for
   anything that reads as a startup complaint rather than a normal
   startup line.

A quick way to line up the two timestamps on Linux::

    tail -n 40 ~/.activity/logs/activity.console.log
    stat -c '%y %n' ~/.auditlog/auditlog.db

On Windows (PowerShell)::

    Get-Content -Tail 40 "$env:LOCALAPPDATA\activity\logs\activity.console.log"
    (Get-Item "$env:LOCALAPPDATA\auditlog\auditlog.db").LastWriteTime

If the console log file itself has grown very large, trim your view
with ``tail``/``Get-Content -Tail`` rather than opening the whole file
in an editor — see *Managing the Service's Console Log Files* for how
large these files can reasonably get before that page's guidance kicks
in.

Making the Copy
================

*Section owner: Platform Tools (Mara Olsen)*

This page does not repeat the full copy procedure — that lives in
*Copying the Database File for Backup* — but the short version, for
context, is:

- confirm the four conditions above,
- quiesce or wait out any active write,
- copy the database file (and any companion journal file present at
  that moment) to the target folder in one operation,
- record the copy's timestamp and source host name in the backup
  folder's naming, and
- move on to verification below in the same sitting.

A copy that sits unverified for a week is a copy nobody actually trusts;
treat verification as the last step of the copy procedure, not a
separate task for later.

Verifying the Copy Opened Cleanly
==================================

*Section owner: Platform Tools (Mara Olsen)*

The goal of verification is narrow: confirm the copy is a complete,
readable SQLite file that a local tool can open without complaint. This
is not a check of what is stored inside it — it is a check that the
container itself is sound.

Step 1 — Compare Size and Timestamp
------------------------------------

Before touching any tool, compare the copy against the source (if the
source is still reachable) or against your own record of what size you
expected.

::

    ls -la /var/lib/auditlog/auditlog.db /var/backups/auditlog/auditlog-20260520.db

A copy that is dramatically smaller than the source, or exactly zero
bytes, failed outright and does not need the rest of this procedure —
go back to *Making the Copy* above and try the copy again.

Step 2 — Open the Copy Read-Only
----------------------------------

Open the copy with the ``sqlite3`` command-line tool in read-only mode
so that verification itself cannot accidentally write to the copy:

::

    sqlite3 -readonly /var/backups/auditlog/auditlog-20260520.db ".tables"

A copy that opened cleanly returns a normal list of table names with no
error text. A copy that did not open cleanly will typically respond
with one of a small number of complaints, most commonly something
about the file not being a database, or about the file being short
(truncated). Either response means the copy is not usable and should be
retaken.

Step 3 — Ask the File to Describe Itself
-------------------------------------------

Follow up with a couple of the SQLite command-line tool's own
meta-commands, which describe the file's structure without reading or
changing any stored content:

::

    sqlite3 -readonly /var/backups/auditlog/auditlog-20260520.db ".schema"
    sqlite3 -readonly /var/backups/auditlog/auditlog-20260520.db ".dbinfo"

``.dbinfo`` in particular reports the page size and page count the file
declares for itself; a page count of zero, or a page size that looks
implausible (not a small power of two), is a strong sign of a copy that
was interrupted mid-write.

Step 4 — Compare a Hash Value Against Your Own Record
--------------------------------------------------------

If you keep a running note of hash values for each backup copy (many
maintainers keep a small text file per host for this), compare the new
copy's hash value against the previous entry to confirm the copy tool
did not silently change anything unexpected in transit — this matters
most for copies made over a network share.

On Linux or macOS::

    sha256sum /var/backups/auditlog/auditlog-20260520.db

On Windows (PowerShell)::

    Get-FileHash "D:\Backups\auditlog\auditlog-20260520.db" -Algorithm SHA256

A hash value on its own does not tell you the copy opened cleanly — a
perfectly consistent hash value of a truncated file will still match a
second truncated copy made the same broken way — so treat this as a
supplement to Steps 2 and 3, not a replacement for them.

Step 5 — Optional: Start a Verification Instance of the Service
-------------------------------------------------------------------

For a copy that will be relied on for anything beyond a quick look,
some maintainers go one step further and point a short-lived,
temporary instance of the loopback service at the copy, using a local
port that does not conflict with the running instance (see *Port
Conflicts on the Loopback Service* above). If the service starts
cleanly against the copy and the console log file shows a normal
startup line rather than a complaint, that is strong confirmation the
copy is usable end to end, not just readable by the command-line tool.

Stop this verification instance as soon as the check is done; there is
no reason to leave a second instance running against a backup copy.

Worked Example
===============

The following walks through a full verification on a small host running
Linux, copying a database file that lives under ``/var/lib/auditlog``.

1. Confirm free space on the backup volume::

       df -h /var/backups

   Output shows 14 GB free on ``/var/backups`` — comfortably above the
   500 MB minimum for this file, which is currently 38 MB.

2. Confirm no write is in progress by checking the console log file for
   a quiet stretch::

       tail -n 20 /var/log/activity/activity.console.log

   The last line is four minutes old, which is long enough to be
   confident nothing is mid-write.

3. Copy the file with a preserving copy command::

       cp --preserve=timestamps /var/lib/auditlog/auditlog.db \
          /var/backups/auditlog/auditlog-20260520.db

4. Compare size::

       ls -la /var/lib/auditlog/auditlog.db /var/backups/auditlog/auditlog-20260520.db

   Both report 38,862,848 bytes. Good sign, not proof.

5. Open the copy read-only and list tables::

       sqlite3 -readonly /var/backups/auditlog/auditlog-20260520.db ".tables"

   Output lists the expected set of names with no error text.

6. Check the file's own reported page count::

       sqlite3 -readonly /var/backups/auditlog/auditlog-20260520.db ".dbinfo"

   Page size 4096, page count 9,487 — consistent with the file size
   above (4096 × 9,487 ≈ 38.9 MB, matching within rounding).

7. Record the hash value::

       sha256sum /var/backups/auditlog/auditlog-20260520.db >> /var/backups/auditlog/hashes.txt

8. Mark the copy as verified in the day's short note — a single line in
   a text file is enough: date, file name, byte count, and "opened
   clean."

The whole worked example above takes under three minutes once a
maintainer has done it a few times.

A Small Helper Script
========================

Several maintainers keep a short shell script in ``scripts/`` to avoid
retyping the steps above by hand. A version close to what is currently
in use::

    #!/usr/bin/env bash
    set -euo pipefail

    SRC="/var/lib/auditlog/auditlog.db"
    OUT="/var/backups/auditlog/auditlog-$(date +%Y%m%d).db"

    cp --preserve=timestamps "$SRC" "$OUT"

    echo "== size check =="
    ls -la "$SRC" "$OUT"

    echo "== open check =="
    sqlite3 -readonly "$OUT" ".tables"

    echo "== structure check =="
    sqlite3 -readonly "$OUT" ".dbinfo"

    echo "== hash =="
    sha256sum "$OUT" | tee -a /var/backups/auditlog/hashes.txt

This is a convenience wrapper only; it does not replace reading the
output, and a maintainer should still eyeball each section rather than
trusting a clean exit code alone — the script does not currently check
its own output for the specific error text mentioned in Step 2 above.

Troubleshooting Common Verification Failures
================================================

.. list-table::
   :header-rows: 1
   :widths: 28 34 38

   * - Symptom
     - Likely Cause
     - What To Do
   * - ``sqlite3`` reports the file is not a database
     - Copy was interrupted, or wrong file was copied
     - Take the copy again after confirming a quiet console log
       stretch; check the copy path was typed correctly
   * - File size is much smaller than expected
     - Target volume ran out of space mid-copy
     - Free space on the target volume, then try again; see disk
       space check above
   * - ``.dbinfo`` page count is zero
     - Copy truncated at the very start
     - Same as above; also confirm the source file path is right
   * - Copy opens but a lock wait appears immediately
     - A second tool already has the copy open
     - Close the other tool fully before reopening the copy
   * - Copy opens cleanly on one host but not another
     - Copy crossed a network share or removable drive that altered
       the file in transit
     - Compare hash values on both ends; copy locally first, then
       move
   * - Hash value does not match the source at copy time
     - Either the copy or the source changed between the two hash
       checks
     - Take the hash of the source immediately before copying, not
       some time before or after
   * - Verification instance of the service will not start against
       the copy
     - Local port already in use by another instance
     - Choose a different local port for the verification instance

Host Monitoring Integration
=============================

*Section owner: Infra Reliability (Sam Okafor)*

Backup copy verification is one of the few upkeep tasks on this list
that is worth folding into a host's regular monitoring rather than
leaving purely to memory. Two things are worth tracking over time on
any host that keeps a database file for ``auditlog``:

- **Age of the last verified copy.** A monitoring check (cron job,
  scheduled task, or whatever the host already uses) that looks at the
  modification time of the most recent entry in the backup folder and
  raises a flag if it is older than the expected copy interval.
- **Result of the last verification, not just the last copy.** A copy
  that exists but never passed Step 2 above is not meaningfully
  different from no copy at all; where possible, have the copy step
  and the verification step write to the same small status file so
  monitoring can tell the two apart.

A minimal status line format that a few hosts already use, one line per
copy, in a plain text file next to the backup folder::

    2026-05-20T09:14:00  size=38862848  opened=clean  hash=6f2a...c19d

Weekly Monitoring Touch Points
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Check
     - What Good Looks Like
     - Owner
   * - Age of last verified copy
     - Under the expected copy interval for that host
     - Infra Reliability
   * - Free space on backup volume
     - Above the 500 MB (workstation) or larger (small host) margin
     - Systems Engineering
   * - Console log file size near copy time
     - No sharp jump right before a copy attempt
     - Developer Experience
   * - Local loopback port free during scheduled verification windows
     - No unexpected listener on the check port
     - Infra Reliability

See *Host Monitoring for auditlog Hosts* for how these fit into the
host's general monitoring, and *Weekly Host Monitoring Checklist* for
the printable version several maintainers keep taped near their desk.

Terminology
============

**Copy**
    A byte-for-byte duplicate of the database file made for backup
    purposes, stored somewhere other than the file's normal working
    location.

**Verification**
    The act of confirming a copy opens cleanly and reports a sound
    internal structure, as distinct from confirming what is stored
    inside it.

**Read-only open**
    Opening a file with a tool set explicitly not to write to it, used
    during verification so the check itself cannot change the copy.

**Journal file**
    A companion file SQLite sometimes leaves next to the main database
    file to track a write that was in progress; its presence or absence
    at copy time affects whether the copy reflects a consistent moment.

**File lock**
    A signal the operating system or SQLite itself uses to coordinate
    access to a file between more than one program at a time.

**Loopback service**
    The part of the package that listens on a local network port and
    answers requests from local programs on the same host only.

**Console log file**
    The rolling text file the service writes describing its own
    startup and ongoing behavior, kept separate from the database file.

**Free space margin**
    The amount of unused disk space a maintainer keeps in reserve on a
    volume beyond what the current file is expected to need.

**Hash value**
    A short fixed-length value computed from a file's full content,
    used to compare two copies of a file without reading the whole
    thing by eye.

**Page count**
    The number of fixed-size internal pages a SQLite file reports for
    itself, used here as a plausibility check against the file's byte
    size.

Files and Paths Referenced
=============================

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Path
     - Type
   * - ``auditlog/``
     - Package directory in the repository root; not modified by any
       procedure on this page
   * - ``README.md``
     - Repository root readme
   * - ``docs/operations-runbooks/backup-copy-verification.rst``
     - This page
   * - ``docs/operations-runbooks/database-file-backup-copy.md``
     - Sibling page covering how the copy itself is made
   * - ``docs/operations-runbooks/sqlite-file-locking.md``
     - Sibling page on lock behavior around the database file
   * - ``docs/operations-runbooks/sqlite-lock-troubleshooting.rst``
     - Sibling page with deeper lock error troubleshooting
   * - ``docs/operations-runbooks/disk-space-checks.md``
     - Sibling page with the disk space threshold table
   * - ``docs/operations-runbooks/console-log-files.md``
     - Sibling page on managing the console log file's growth
   * - ``docs/operations-runbooks/host-monitoring-overview.md``
     - Sibling page tying host checks together
   * - ``docs/operations-runbooks/port-conflicts.md``
     - Sibling page on diagnosing local port conflicts
   * - ``scripts/verify-backup-copy.sh``
     - Optional helper script wrapping the copy and open-and-check
       steps described here
   * - ``/var/lib/auditlog/auditlog.db`` (or ``~/.auditlog/auditlog.db``
       on a workstation)
     - Default location of the live database file
   * - ``/var/log/activity/activity.console.log`` (or
       ``~/.activity/logs/activity.console.log`` on a workstation)
     - Default location of the console log file
   * - ``/var/backups/auditlog/`` (or a mapped drive such as
       ``D:\Backups\auditlog\`` on Windows)
     - Common target folder for copies made under this procedure

Tools and Package Versions
=============================

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Tool / Package
     - Version
     - Purpose
   * - ``auditlog``
     - 0.9.4
     - The package whose database file is being copied and verified
   * - Python interpreter
     - 3.11.9
     - Runs the package; standard library only, no outside packages
   * - ``sqlite3`` command-line tool
     - 3.45.1
     - Opens and describes the copy during verification
   * - ``rsync``
     - 3.2.7
     - Alternative copy tool for network-share copies (Linux/macOS)
   * - ``robocopy``
     - built into Windows (no separate version)
     - Alternative copy tool for network-share copies (Windows)
   * - PowerShell
     - 5.1
     - Runs the Windows-side checks shown in this page
   * - ``ss``
     - iproute2 6.6
     - Checks local port use on Linux
   * - ``Get-NetTCPConnection``
     - built into Windows (PowerShell module)
     - Checks local port use on Windows

Change Log
===========

* **2026-05-20 — v1.0.2** — Added the local port check to Step 5, after
  a maintainer started a verification instance without checking for a
  conflict and lost several minutes chasing the wrong cause.
* **2026-03-08 — v1.0.1** — Reworded the disk space guidance to point
  at the current threshold table instead of repeating an old number
  that had drifted out of date.
* **2025-12-15 — v1.0.0** — First version marked stable for general
  use; added the worked example and the troubleshooting table.
* **2025-10-02 — v0.9.0** — Added the hash value comparison step and
  the small helper script.
* **2025-08-19 — v0.8.0** — Split this page out of the general backup
  copy page so verification had its own home; added the ``.dbinfo``
  step.
* **2025-06-11 — v0.7.0** — Added the host monitoring integration
  section and weekly touch points table.
* **2025-04-28 — v0.6.0** — Initial short draft covering only the
  read-only open check.

Related Pages
==============

- *operations-runbooks Overview*
- *Copying the Database File for Backup*
- *Handling SQLite File Locking on the Database File*
- *Troubleshooting SQLite Lock Errors*
- *Checking Disk Space Around the Database File*
- *Managing the Service's Console Log Files*
- *Diagnosing Port Conflicts for the Loopback Service*
- *Default Loopback Port Numbers and How to Change Them*
- *Host Monitoring for auditlog Hosts*
- *Weekly Host Monitoring Checklist*
- *Workstation and Small Host Upkeep Overview*
