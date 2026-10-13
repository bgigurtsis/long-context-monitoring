# Developer Handbook Terminology Comparison

Scope: every file found under `maintenance/inputs/developer-handbook/`, read in full. No
application code or files outside this folder were consulted.

| File | Self-declared title | Version | Last updated |
|---|---|---|---|
| `README.md` | Developer Handbook Overview | 3.1 | 2026-05-12 |
| `code-review-conventions.md` | Code Review Conventions | 4.0 | 2025-06-30 |
| `coding-style-guide.md` | Coding Style Guide | 3.5 | 2025-03-22 |
| `commit-message-style.md` | Commit Message Style | 1.3 | 2024-12-01 |
| `dependency-management.txt` | Dependency Management | 1.4 | 2026-02-18 |
| `editor-configuration.md` | Editor Configuration | v1.2.0 | 2024-09-14 |
| `lint-formatting-config.yaml` | Lint and Formatting Configuration | v1.0.1 | 2026-04-01 |
| `linux-setup-notes.txt` | Linux Setup Notes | 0.9 | 2024-05-27 |
| `local-database-file-notes.md` | Local Database File Notes | 1.6 | 2025-10-05 |
| `logging-conventions.md` | Logging Conventions | 2.1 | 2024-07-19 |
| `python-version-support.md` | Supported Python Versions | 1.7 | 2026-01-20 |
| `workstation-setup.md` | Workstation Setup | 2.4 | 2025-11-03 |

All 12 of these files carry their own "Terminology" or "Terminology and Glossary" section
and were compared term by term below.

**Note on missing files:** ten of the twelve documents' own Related Pages / Files-referenced
sections cite `windows-setup-notes.rst` and `macos-setup-notes.rst` by name and version
(e.g. `README.md` lists "Windows Setup Notes — Version 1.1" and "macOS Setup Notes — Version
1.0"; `dependency-management.txt`, `coding-style-guide.md`, `python-version-support.md`,
`local-database-file-notes.md`, and `workstation-setup.md` all do the same). Neither file
exists in `maintenance/inputs/developer-handbook/` — only `linux-setup-notes.txt` is present
among the three platform pages. Any glossary those two pages might have defined can't be
checked against the ten that are here.

## Where the glossaries agree

- **Virtual environment.** `README.md`, `dependency-management.txt`, `lint-formatting-config.yaml`,
  `linux-setup-notes.txt`, `python-version-support.md`, and `workstation-setup.md` all define
  a virtual environment (or "venv") as an isolated Python environment/installation created
  with the standard library's `venv` module, kept separate from the system interpreter or
  other projects. The core idea is consistent across all six.
- **Local database file.** `README.md` ("SQLite database file"), `code-review-conventions.md`
  ("Local database file"), `coding-style-guide.md` ("Database file"), `editor-configuration.md`
  ("Local database file"), `local-database-file-notes.md` ("Database file"), and
  `workstation-setup.md` ("Local database file") all agree it is a single local SQLite file
  that persists the service's/package's operational state, distinct from any code file or
  remote database.
- **Loopback service.** `coding-style-guide.md`, `editor-configuration.md`, and
  `workstation-setup.md` all describe it consistently as the local-only HTTP service the
  package runs on the loopback interface/`localhost`, not reachable from other machines.
- **Pull request (core concept).** `README.md`, `code-review-conventions.md`,
  `linux-setup-notes.txt`, and `workstation-setup.md` agree a pull request is a proposed
  change, opened for review, that must be reviewed/discussed before merging into the
  main/default branch.
- **Working tree.** `coding-style-guide.md` ("the set of files checked out from the
  repository on your local machine") and `workstation-setup.md` ("the checked-out files on
  disk for a git repository, as opposed to the git object store or the remote") agree.
- **Workstation.** `README.md` ("A developer's local machine ... configured for oauthsvc
  development") and `workstation-setup.md` ("the personal or team-issued machine a
  contributor develops on, as distinct from any shared build or CI machine") agree.
- **Feature branch.** `linux-setup-notes.txt` and `workstation-setup.md` agree it's a
  short-lived branch for one piece of work, merged via pull request and then removed/merged.
- **Linting (as a process).** `README.md` ("running static analysis tools that examine code
  without executing it") and `linux-setup-notes.txt` ("Automated static analysis of code to
  detect style violations, unused imports, and potential bugs") describe the same activity,
  even though (see below) they disagree on which literal tool performs it.

## Where the glossaries differ

### 1. Which tool "the linter" and "the formatter" actually are

The glossaries split into three incompatible pairings of actual tool names, even though most
of them use the generic terms "linter" and "formatter" as if there were one obvious answer:

- **Black formats, Ruff lints (two separate tools).** `README.md`'s Tools and Versions table
  (Black 23.0 as "Code formatter", Ruff 0.1 as "Fast Python linter"), `coding-style-guide.md`
  (Black 24.4.2 "Formatter that owns line wrapping...", Ruff 0.4.4 "Linter for unused
  imports..."), and `code-review-conventions.md` (ruff 0.6.9 "lint checks run before human
  review", black 24.4.2 "format checking, run alongside ruff") all agree on this pairing.
- **Ruff does both.** `editor-configuration.md`'s glossary says "Formatter ... also handled
  by ruff in this project's current configuration" and "Linter ... ruff plays this part for
  acctsvc" (note the typo — "acctsvc" rather than "oauthsvc" — in that same glossary entry).
  `workstation-setup.md`'s Tools table lists a single line, "ruff 0.6.9 | Linting and
  formatting", and its Coding Style section instructs `ruff format .` and `ruff check .`
  with no mention of Black at all.
- **Black formats, Flake8 lints, isort sorts imports — no Ruff.** `dependency-management.txt`'s
  Tools table (Black 23.7.0, Flake8 6.0.0), `lint-formatting-config.yaml`'s glossary
  ("Black ... referenced in this documentation as 'formatter'"; "Flake8 ... referenced here
  as 'linter'"), and `linux-setup-notes.txt` (glossary lists "Tools: flake8, black, isort"
  under "Linting", and its commands are `black .`, `isort .`, `flake8 ... --max-line-length=88`)
  never mention Ruff.

A new contributor reading only `dependency-management.txt`, `lint-formatting-config.yaml`, or
`linux-setup-notes.txt` would install Flake8; reading only `editor-configuration.md` or
`workstation-setup.md` would install only Ruff; reading `README.md` or `coding-style-guide.md`
would install both Black and Ruff. All twelve documents describe themselves as documenting
the same repository's tooling.

### 2. Whether a pre-commit hook is actually shipped

`editor-configuration.md`'s glossary states plainly: "Pre-commit hook — a git-managed script
that runs automatically before a commit is created; **oauthsvc does not currently ship one**,
though it has been discussed more than once."

This is contradicted or complicated by several other documents:

- `README.md`'s glossary defines the term generically and its Tools and Versions table lists
  "Pre-commit | 2.20 | Git hook framework that automates running linters and formatters
  before commits" without qualifying it as unshipped.
- `linux-setup-notes.txt`'s glossary ("Configured via pre-commit framework") and body ("pip
  install pre-commit", "pre-commit install") present it as something a developer actually
  sets up and runs.
- `code-review-conventions.md` (step 1, "Before You Open a Pull Request") says "Most
  contributors have `pre-commit` wired in already", treating it as commonly present.
- `workstation-setup.md`'s Tools table lists "pre-commit | 3.7.1 | Optional local hook runner
  for lint checks before commit" — optional, but present as a real, usable tool.
- `lint-formatting-config.yaml` complicates this further on its own: its
  `pre_commit_workflow` section states "The repository includes a pre-commit hook
  configuration," but its own `repository_file_manifest` lists `.pre-commit-config.yaml` as
  "Configuration for pre-commit hooks **(in-progress integration)**" — an internal hedge
  between "included" and "in progress."

### 3. The line length budget: 88 vs. 100

`coding-style-guide.md`'s own glossary fixes this term precisely: "Line length budget — the
maximum number of characters allowed on a single line before the formatter wraps it; **88**
for this package." This is corroborated by `lint-formatting-config.yaml` ("[tool.formatter]:
Specifies line length (88 characters)..." and "Maximum line length: 88 characters"),
`editor-configuration.md` (`"editor.rulers": [88]`), and `linux-setup-notes.txt`'s flake8
invocation (`--max-line-length=88`).

`workstation-setup.md` disagrees with all of them: its VS Code snippet sets
`"editor.rulers": [100]`, its "Recommended settings by editor" table lists "100" as the line
length ruler for every editor, and its own Coding Style section states "Line length: 100
characters, matching the editor ruler configured above." Nothing in `workstation-setup.md`
acknowledges the other pages' 88-character figure.

Separately, `editor-configuration.md` cites the ruler as "matching the line-length convention
documented in the Coding Style Guide (**v3.4**)" — but `coding-style-guide.md`'s own header
identifies itself as version **3.5**, so the citation points at a version one behind the
document's own stated current version.

### 4. The quoted `.editorconfig` contents don't match across documents

Three documents quote what each presents as the repository-root `.editorconfig` file:
`coding-style-guide.md`, `editor-configuration.md`, and `workstation-setup.md`. All three
agree on the `[*]` block (4-space indent, LF line endings, UTF-8, trim trailing whitespace,
insert final newline) and the `[*.md]` exception (trailing whitespace not trimmed). Only
`editor-configuration.md`'s copy includes an additional section:

```
[*.yaml]
indent_size = 2
```

This section is absent from the otherwise-matching copies quoted in `coding-style-guide.md`
and `workstation-setup.md`.

### 5. Inconsistent granularity for "venv" vs. "Virtual environment"

`dependency-management.txt` defines "venv (virtual environment)" as one entry and then
separately lists "Virtual environment: See venv" — treating the two spellings as pure
synonyms of a single concept. `linux-setup-notes.txt` instead defines them as two distinct
things: "Virtual Environment" is the isolated installation concept, while "venv" is
specifically "Standard Python module and the directory containing a virtual environment."
`python-version-support.md`'s definition additionally narrows the purpose of a virtual
environment to isolating "developer-side tooling" specifically (consistent with that page's
framing that the package itself has no runtime dependencies), whereas `README.md` and
`workstation-setup.md` describe it more broadly as isolating "project dependencies" or "a
project's installed packages" in general.

### 6. Pull request: inconsistent branch terminology, and an uncorroborated synonym

The four glossaries that define "Pull request" each name the target branch differently:
`README.md` says "the main development branch," `code-review-conventions.md` says "the
default branch," `linux-setup-notes.txt` says "main," and `workstation-setup.md` says "the
main branch."

`workstation-setup.md`'s entry also adds a claim no other document supports: "used
interchangeably with 'review request' on this team." `code-review-conventions.md` — the page
whose entire subject is the pull request review process, at roughly 8,000 words — never uses
the phrase "review request" anywhere.

### 7. The local database file's identity conflicts across the two documents most focused on it

Both `local-database-file-notes.md` and `workstation-setup.md` define "Local database
file"/"Database file" in their glossaries as the single SQLite file holding the service's
state, and both agree on the concept. But the concrete details their surrounding pages give
for that same term conflict:

- `local-database-file-notes.md` names the file `oauthsvc.db`, located at
  `~/.oauthsvc/oauthsvc.db` (macOS/Linux) or `%USERPROFILE%\.oauthsvc\oauthsvc.db` (Windows),
  overridable via an unnamed "database path environment variable."
- `workstation-setup.md` gives entirely different per-platform paths — `~/.local/share/oauthsvc/state.db`
  (Linux), `~/Library/Application Support/oauthsvc/state.db` (macOS), and
  `%LOCALAPPDATA%\oauthsvc\state.db` (Windows) — naming the file `state.db`, not `oauthsvc.db`,
  and overridable via a specifically-named variable, `PLATSVC_STATE_DIR`.

Two documents that each formally define the same glossary term point to a different
filename, a different directory layout, and a differently-named override variable for what
is supposed to be the one local database file the service uses.

### 8. Naming headword inconsistency for the same database-file concept

Beyond point 7's factual conflict, the six documents that define this concept don't even
agree on what to call the glossary headword itself: "SQLite database file" (`README.md`),
"Database file" (`coding-style-guide.md`, `local-database-file-notes.md`), and "Local
database file" (`code-review-conventions.md`, `editor-configuration.md`,
`workstation-setup.md`). Notably, `dependency-management.txt` discusses the database file at
length in its body text but does not define any of these headwords in its own glossary at
all.

## Minor, single-document terms (no cross-document conflict found)

A number of terms are defined in only one glossary, with no other document's glossary using
or contradicting them: "Ambient dependency," "External dependency," "Stdlib," "Module," and
"CI/CD" (all `dependency-management.txt`); "Handler function," "Naming case," and "Draft pull
request" (all `coding-style-guide.md`); "Floor version," "Sunset," and "Bundled SQLite
library" (all `python-version-support.md`); "Console filter" and "File filter" (both
`logging-conventions.md`); "WAL mode" and "Read-only mode" (both `local-database-file-notes.md`).
These are internally consistent simply because nothing elsewhere in the folder engages with
them.
