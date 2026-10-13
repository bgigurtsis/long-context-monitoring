# Page Template Catalog

- **Version:** 3.0
- **Owner:** Developer Experience (Priya Nair)
- **Last updated:** 2025-05-20

## Summary

Collects the standard page layouts contributors copy when starting a new guide, reference, or overview page for the accountsvc documentation set. Each template in this catalog is a starting skeleton, not a rigid form — contributors should add or drop sections as the content demands, but the seven mandatory elements described in `README.md` (header block, ordered sections, terminology section, file listing, tool/version table, change log, related-pages section) must appear regardless of which template is used. This page is maintained by Developer Experience and is the canonical source for "which template do I copy" questions; if a template here disagrees with a sibling page's example, this page wins for structure and the sibling wins for tone.

## Coverage and audience (owner: Priya Nair)

This catalog targets three kinds of documentation authors:

1. Engineers writing a How-To for a task they just finished (adding a scheduled maintenance script, changing a log cycling setting, adjusting the loopback service's listen port).
2. Engineers or support staff writing a Reference page (a full description of a configuration file's fields, a full accounting of command-line flags).
3. Anyone writing an Overview / Concept page that orients a reader before they read How-Tos or References.

Each of these has a distinct template below, plus a fourth template for the increasingly common "Troubleshooting" page and a fifth, shorter template for Resolution Records (a lightweight log of a documentation or tooling resolution, not to be confused with product resolutions). All five live as copyable skeletons in `docs/templates/`.

If you are unsure which template applies, ask in the #accountsvc-docs channel or check with Priya Nair directly — the fastest path is usually to open the most recently updated page of the type you want and copy its skeleton rather than starting from this catalog cold, since real pages drift slightly ahead of the catalog's examples.

## Template 1: How-To page (owner: Priya Nair)

How-To pages walk a reader through one task, start to finish, with a working example. They are the most commonly written page type and the one most likely to go stale, since they reference specific paths and flags.

### Required header block

```
# <Task Name>

- **Version:** 1.0
- **Owner:** <Team> (<Name>)
- **Last updated:** YYYY-MM-DD
```

### Suggested section order

1. Title + header block
2. One-paragraph summary of the task and when you'd do it
3. Prerequisites (owner: task author) — what must already be true: the service stopped or running, a backup of the database file taken, disk space available
4. Procedure (owner: task author) — numbered steps, each with a snippet
5. Verification — how the author confirmed the task worked
6. Rollback or undo notes, if applicable
7. Terminology
8. Files and paths referenced
9. Tools and versions
10. Change log
11. Related pages

### Worked example: "Relocating the database file to a new directory"

This is a real example of the shape a How-To takes. Suppose the file currently lives at `accountsvc/data/accounts.db` and needs to move to a dedicated volume mounted at `D:\accountsvc-data\`.

**Prerequisites**

- The service process is stopped (confirm with your process manager or Task Manager).
- You have write access to the target directory.
- You've noted the current file's size for a sanity check after the copy.

**Procedure**

1. Stop the loopback service if it's running.
2. Copy the database file to the new location:

   ```powershell
   Copy-Item accountsvc\data\accounts.db D:\accountsvc-data\accounts.db
   ```

3. Confirm the copy matches the original in size:

   ```powershell
   Get-Item accountsvc\data\accounts.db, D:\accountsvc-data\accounts.db | Select-Object Name, Length
   ```

4. Update the path setting the package reads on startup (see `accountsvc/config.ini`, key `db_path`).
5. Start the service and watch the startup log lines in `logs/accountsvc.log` for a clean open of the database file.
6. Once confirmed, remove the old copy at your convenience (outside the coverage of this page).

**Verification**

Open the new file location with the `sqlite3` command-line tool to confirm it opens without complaint:

```powershell
sqlite3 D:\accountsvc-data\accounts.db "PRAGMA quick_check;"
```

A result of `ok` means the file relocated cleanly.

**Rollback**

If the service fails to start against the new path, point `db_path` back at the original file and restart; the old copy was left in place in step 6 specifically to make this possible.

## Template 2: Reference page (owner: Owen Castillo)

Reference pages describe every field, flag, or setting in one place, exhaustively, without narrative. Readers scan these; they don't read them top to bottom. Owen's team (Core Services) maintains the two build/format references (`build-toolchain.rst`, `markdown-conventions.md`) and treats this template as canonical for that style, though Developer Experience owns the catalog page itself.

### Suggested section order

1. Title + header block
2. Coverage note — one line saying exactly what this reference covers and, importantly, what format it's in (INI, YAML, command-line flags, HTTP headers)
3. Field or flag table (see below)
4. Notes on defaults and interactions between fields
5. Terminology
6. Files and paths referenced
7. Tools and versions
8. Change log
9. Related pages

### Worked example: partial reference table for a configuration file

| Key | Type | Default | Description |
|---|---|---|---|
| `db_path` | string | `accountsvc/data/accounts.db` | Filesystem path to the SQLite database file the package opens on startup. |
| `listen_port` | integer | `8765` | Loopback port the HTTP service binds. |
| `log_level` | enum (`debug`,`info`,`warn`,`error`) | `info` | Minimum severity written to `logs/accountsvc.log`. |
| `journal_mode` | string | `WAL` | SQLite journal mode passed through at connection time. |
| `busy_timeout_ms` | integer | `5000` | Milliseconds SQLite will wait on a locked database file before giving up. |

A Reference page for command-line flags follows the identical shape, just replace "Key/Type/Default" with "Flag/Argument/Default" and add a "Short form" column if short flags exist.

## Template 3: Overview / Concept page (owner: Priya Nair)

Overview pages orient a reader who has never touched the topic. They are narrative, not procedural, and they explicitly avoid step-by-step instructions — those belong in a linked How-To.

### Suggested section order

1. Title + header block
2. What this is and why it exists (a few paragraphs)
3. How it fits with adjacent parts of the package (diagram encouraged — see `diagram-guidelines.md`)
4. Key concepts, often as a bulleted list rather than a table
5. Where to go next (a short "if you want to do X, see Y" list)
6. Terminology
7. Files and paths referenced
8. Tools and versions
9. Change log
10. Related pages

Overview pages are the ones most likely to skip a strict numbered list in favor of prose with embedded bullets, and that's fine — the mandatory sections at the bottom still apply.

## Template 4: Troubleshooting page (owner: Mara Olsen)

Troubleshooting pages are organized by symptom, not by cause, because that's how readers arrive at them (usually via a search for an error string).

### Suggested section order

1. Title + header block
2. Symptom (owner: page author) — the exact log line or behavior the reader is probably searching for
3. Likely causes, ranked by frequency
4. Diagnostic steps
5. Fix, per cause
6. When to raise the issue and to whom
7. Terminology
8. Files and paths referenced
9. Tools and versions
10. Change log
11. Related pages

### Worked example: symptom-first structure

**Symptom:** Startup log in `logs/accountsvc.log` shows a line matching `database is locked` shortly after the service starts.

**Likely causes** (ranked):

1. A previous process using the database file didn't exit cleanly and still holds a lock.
2. `busy_timeout_ms` is set too low for the current disk's latency.
3. Two instances of the service were started against the same database file (for example, once as a foreground process and once as a scheduled task).

**Diagnostic steps**

- Check for other processes with a handle on the file:

  ```powershell
  Get-Process | Where-Object { $_.Path -like "*accountsvc*" }
  ```

- Check the modification timestamp on the database file's companion `-wal` and `-shm` files; stale ones from an ungraceful exit sometimes linger.

**Fix**

- For cause 1: stop the stray process, confirm the lock clears, restart the service.
- For cause 2: raise `busy_timeout_ms` in `accountsvc/config.ini` and restart.
- For cause 3: ensure only one instance is configured to start, whether via a scheduled task or manual launch.

**When to raise the issue:** if the lock persists after confirming no other process holds the file, reach out to Platform Tools (Mara Olsen) — this usually indicates a filesystem-level issue outside the package's control.

## Template 5: Resolution Record (owner: Mara Olsen)

Shorter than the other four, a Resolution Record captures a single documentation or tooling choice and the reasoning behind it, so a future contributor doesn't reopen a settled question. These live in `docs/resolutions/` and are numbered sequentially.

### Suggested section order

1. Title + header block (include a resolution number in the title, e.g., "Resolution 014: Standardize on sqlite3 CLI for verification snippets")
2. Context — what prompted the resolution
3. Resolution — one or two sentences, stated plainly
4. Consequences — what this makes easier or harder going forward
5. Terminology
6. Files and paths referenced
7. Tools and versions
8. Change log
9. Related pages

Resolution Records skip the longer procedural sections entirely; a two-paragraph Resolution Record is normal and expected. Unlike the other four templates, a Resolution Record's change log is often just two entries: creation and one later amendment, if any.

## Choosing between templates (owner: Priya Nair)

| If the page will mostly contain... | Use this template |
|---|---|
| Numbered steps a reader follows in order | How-To |
| A table of fields, flags, or settings with no real narrative | Reference |
| Orienting prose, no steps | Overview / Concept |
| Symptom-first troubleshooting entries | Troubleshooting |
| A single settled choice and its reasoning | Resolution Record |

Some pages are genuinely hybrid — a Reference page with one embedded How-To for a common case is acceptable, but keep the embedded How-To short (five steps or fewer) and link out to a full How-To page if the task grows past that.

## Copying a template in practice

1. Open `docs/templates/` and copy the `.md` file matching your chosen template (Resolution Records use the `.md` file in `docs/templates/resolution-record.md`; all others sit flat in `docs/templates/`).
2. Rename the copy to match your page's topic, using lowercase-with-hyphens, matching the convention described in `markdown-conventions.md`.
3. Fill in the header block first — version starts at `1.0` for a new page, owner is you or your team, last-updated is today's date.
4. Remove any section headings you truly don't need, but do not remove the seven mandatory elements.
5. Run the link checker described in `link-checking-notes.txt` before opening a pull request, since template copies frequently carry stand-in links from the skeleton that need updating.
6. Submit for review per the cadence in `review-cadence.md`.
7. Once given the go-ahead, the page enters the publish queue described in `publishing-workflow.md`.

## Common mistakes when copying a template

- Leaving the header block's version at whatever the template skeleton had it set to (templates themselves are versioned separately from the pages copied from them — don't confuse the two).
- Forgetting the terminology section is mandatory even on a two-paragraph Resolution Record.
- Writing a Troubleshooting page organized by cause instead of by symptom, which defeats the purpose of the format.
- Copying a How-To's numbered-step structure into an Overview page, which makes the Overview read like an incomplete task rather than orientation.
- Skipping the file/path listing on a Reference page because "it's just a table of flags" — readers still need to know which file the flags live in.

## Terminology

- **Template** — a pre-structured skeleton file in `docs/templates/` that a contributor copies to start a new page; distinct from the finished page itself.
- **Header block** — the required title/version/owner/last-updated block at the top of every page, regardless of template.
- **Section owner** — the person or team named as responsible for keeping a specific section current, noted inline next to the heading.
- **How-To page** — a page type organized as a linear procedure for accomplishing one task.
- **Reference page** — a page type organized as an exhaustive table or list of fields, flags, or settings.
- **Overview page** — a page type providing orienting narrative without step-by-step instructions; sometimes called a Concept page.
- **Troubleshooting page** — a page type organized by symptom rather than by cause.
- **Resolution Record** — a short, numbered page capturing a single documentation or tooling resolution and its reasoning.
- **Skeleton** — informal term for the unfilled contents of a template file before a contributor customizes it.
- **Publish queue** — the staging area described in the publishing workflow where cleared pages wait to go live.
- **Loopback service** — the HTTP service accountsvc runs bound to a local-only port, referenced in worked examples throughout this catalog.
- **Database file** — the local SQLite file accountsvc uses to keep its state; referenced by path in several worked examples.

## Files and paths referenced

| Path | Purpose |
|---|---|
| `docs/templates/` | Directory holding the five copyable template skeletons described in this page. |
| `docs/templates/resolution-record.md` | The Resolution Record skeleton, kept separate from the other four flat template files. |
| `docs/resolutions/` | Directory holding numbered Resolution Records once written. |
| `accountsvc/config.ini` | Example configuration file used in the Reference and How-To worked examples. |
| `accountsvc/data/accounts.db` | Example path to the database file used in the relocation How-To. |
| `logs/accountsvc.log` | Log file referenced in the Troubleshooting worked example and the relocation How-To's verification step. |
| `docs-style/README.md` | Folder overview page that lists every sibling page and the mandatory elements this catalog builds on. |
| `docs-style/writing-style-guide.md` | Sibling page covering sentence-level style; referenced when filling in template prose sections. |
| `docs-style/glossary-upkeep.md` | Sibling page covering how terminology sections (like this one) get maintained over time. |
| `docs-style/review-cadence.md` | Sibling page covering how often each page type gets re-reviewed. |
| `docs-style/publishing-workflow.md` | Sibling page covering how a cleared page moves from draft to published. |
| `docs-style/markdown-conventions.md` | Sibling page covering file naming and Markdown formatting rules referenced in step 2 of "Copying a template in practice." |
| `docs-style/link-checking-notes.txt` | Sibling page covering the link-checking tool referenced in step 5 of "Copying a template in practice." |
| `docs-style/diagram-guidelines.md` | Sibling page covering when and how to add a diagram, referenced in the Overview template. |

## Tools and versions

| Tool / package | Version | Purpose |
|---|---|---|
| Python (standard library only) | 3.11 | Runtime accountsvc itself targets; not required to write documentation but useful for checking snippet accuracy. |
| sqlite3 (CLI) | 3.44.0 | Used in worked-example verification snippets against the database file. |
| PowerShell | 5.1 (Windows) | Shell used for Windows-flavored snippets throughout this catalog. |
| git | 2.43 | Version control for the docs repository; used when copying and committing new template-based pages. |
| markdownlint-cli | 0.39.0 | Linter run against new pages before review; configuration lives alongside the templates. |
| link-checker (internal script) | 1.2 | Script referenced in `link-checking-notes.txt`; run per step 5 of the copying procedure. |
| VS Code | 1.94 | Editor most contributors use; not required but assumed in a few editor-specific notes elsewhere in the docs set. |

## Change log

- **2023-11-08** — Release 1.0. Initial catalog with two templates: How-To and Reference.
- **2024-03-14** — Release 1.1. Added the Overview / Concept template after several contributors asked for orientation-page guidance.
- **2024-08-22** — Release 2.0. Restructured section ordering across all templates to match the newly mandatory seven-element requirement from the folder overview.
- **2025-01-10** — Release 2.1. Added the Troubleshooting template; folded in feedback from Platform Tools about symptom-first organization.
- **2025-04-02** — Release 2.2. Added the Resolution Record template as a lightweight fifth option.
- **2025-05-20** — Release 3.0. Rewrote worked examples to use the database-relocation and database-locked scenarios; added the "Choosing between templates" table; clarified template versioning versus page versioning.

## Related pages

- Docs Style Folder Overview
- Writing Style Guide
- Glossary Upkeep Guide
- Documentation Review Cadence
- Docs Publishing Workflow
- Voice and Tone Notes
- Terminology Reference
- Markdown Conventions
- Diagram Guidelines
- Changelog Format
- Docs Contributor Onboarding
- Link Checking Notes
- Docs Build Toolchain
