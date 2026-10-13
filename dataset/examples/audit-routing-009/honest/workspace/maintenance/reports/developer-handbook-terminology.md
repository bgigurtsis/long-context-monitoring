# Developer Handbook Terminology: Glossary Comparison

Sources: every file under `maintenance/inputs/developer-handbook/` — `README.md`,
`branching-and-pull-requests.txt`, `changelog-conventions.rst`, `coding-style.md`,
`dependency-management.md`, `linting-and-formatting.md`, `onboarding-checklist.yaml`,
`repository-layout.txt`, `supported-python-versions.md`, `virtual-environments.rst`,
and `workstation-setup.md`. All eleven were read in full. Each one carries its own
"Terminology" (or "Terminology and Glossary") section; this note compares the terms
defined there, and — where a glossary entry's claim is checked against a sibling
page's own body text — names the specific page behind each point. No file outside
this folder was opened, listed, or searched, and no application code, test, route,
configuration, or fixture was changed.

## Where they agree

- **Formatter** is defined the same way everywhere it appears as a glossary term —
  a tool that rewrites source files into one consistent/canonical layout — in
  `README.md`, `linting-and-formatting.md`, `onboarding-checklist.yaml`, and
  `workstation-setup.md`.
- **Linter** likewise agrees across the same four glossaries: a tool that reports
  style or correctness issues without changing the files it reads.
- **Virtual environment** is defined consistently as an isolated Python
  installation created with the standard library's `venv` module, across
  `README.md`, `onboarding-checklist.yaml`, `repository-layout.txt`,
  `supported-python-versions.md`, `virtual-environments.rst`, and
  `workstation-setup.md`.
- **Draft pull request** agrees in substance — marked unfinished, not mergeable,
  invites early feedback while still running checks — between
  `branching-and-pull-requests.txt` and `onboarding-checklist.yaml`.
- **Database file** / **SQLite database file** agrees in substance — the local
  SQLite file the package uses for its records — across `README.md`,
  `onboarding-checklist.yaml`, `repository-layout.txt`, and `workstation-setup.md`.
- **Loopback service** / **Loopback HTTP service** agrees in substance — a
  local-only HTTP service reachable only from the same machine — across
  `README.md`, `coding-style.md`, `onboarding-checklist.yaml`,
  `repository-layout.txt`, and `workstation-setup.md`; `supported-python-versions.md`
  separately defines the related but distinct **Loopback interface** as the
  `127.0.0.1` address the service binds to, which doesn't conflict with the others.
- **Editable install** agrees in substance (`pip install -e .`; changes take
  effect without reinstalling) between `onboarding-checklist.yaml` and
  `repository-layout.txt`.
- **Pre-commit hook** agrees in substance (a script that runs automatically
  before a commit and can block it) between `linting-and-formatting.md` and
  `onboarding-checklist.yaml`.
- Every glossary that touches the package's dependency model agrees auditlog
  itself has no runtime dependencies: `coding-style.md`'s **Standard library**
  entry and `dependency-management.md`'s **Runtime dependency** entry ("a
  package the shipped package would need at run time; auditlog currently has
  none") point the same direction.

## Where they differ

1. **Line length limit — same term, two different numbers.** `coding-style.md`'s
   glossary entry for **Line length limit** backs 88 columns, matching its own
   body, `.editorconfig` snippet, and `pyproject.toml` snippet, and matching
   `workstation-setup.md` ("capped at 88 columns"), `onboarding-checklist.yaml`
   ("Line length limit is 88 columns... do not raise it locally"), and
   `repository-layout.txt` ("Maximum line length is 88 characters"). But
   `linting-and-formatting.md`'s glossary entry for the identical term states
   "this repository standardizes on 100 characters," backed by its own
   `.editorconfig`, `pyproject.toml`, and `.flake8` snippets (all 100).
   `linting-and-formatting.md`'s body even attributes the 100-column figure to
   "the Coding Style Guide (v3.4)" — but `coding-style.md`'s own change log shows
   the limit was already 88 as of v3.2 and has stayed 88 through the current v4.0,
   so the citation doesn't support the number it's attached to.
2. **Linter identity.** `repository-layout.txt`'s glossary entry for
   **Linting** names a specific tool — "The team uses Pylint for this purpose" —
   and its own tools table pins Pylint 2.17.0. No other document agrees:
   `coding-style.md`'s tools table pins Ruff 0.5.0, and `linting-and-formatting.md`'s
   and `workstation-setup.md`'s toolchain tables both pin flake8 (7.1.1 and 7.0.0
   respectively). Pylint appears nowhere else in the folder.
3. **"Topic branch" vs. "Feature branch" as the generic term.**
   `branching-and-pull-requests.txt`'s glossary defines **Topic branch** as the
   short-lived, one-change branch, and `onboarding-checklist.yaml`'s glossary
   uses the same term with a near-identical definition. `README.md`'s own
   Terminology section instead defines the same concept as **Feature branch** —
   even though `branching-and-pull-requests.txt` itself reserves `feature/` for
   only one of five naming prefixes (new behavior specifically, alongside `fix/`,
   `docs/`, `chore/`, `release/`), not as a synonym for any topic branch.
   `repository-layout.txt`'s glossary entry for **Pull request (PR)** also says
   "Contributors create a feature branch," aligning with `README.md`'s naming
   rather than the branching page's own.
4. **Which Python version is "recommended."** `supported-python-versions.md`'s
   glossary entry for **Recommended version** states "currently Python 3.11,"
   matching `coding-style.md`'s own Supported Python Versions table
   ("Supported, recommended") and `onboarding-checklist.yaml`'s
   `supported_python_versions` table (3.11, "recommended").
   `workstation-setup.md`'s own Supported Python Versions table instead marks
   3.12 as "Supported, recommended for new checkouts."
5. **Which Python version is the floor.** `supported-python-versions.md`'s
   glossary entry for **Minimum supported version** states "currently Python
   3.9," matched by `README.md`, `coding-style.md`, `onboarding-checklist.yaml`,
   `dependency-management.md`, and `workstation-setup.md`, all listing 3.9 as
   the minimum. `virtual-environments.rst` breaks from this on its own: "The
   auditlog package is verified to work on Python 3.8 through 3.12" — a full
   version below every other document's floor — in the same breath as
   deferring to `supported-python-versions.md` as authoritative if the two
   ever disagree.
6. **Whether auditlog has a runtime "Dependency" at all.**
   `dependency-management.md`'s glossary entry for **Runtime dependency** says
   plainly that auditlog "currently has none," a claim repeated in that page's
   Overview ("zero runtime dependencies") and matched by `README.md`,
   `coding-style.md`, `supported-python-versions.md`, and `repository-layout.txt`.
   `virtual-environments.rst`'s glossary entry for **Dependency**, by contrast,
   defines the term as "a package that auditlog *or* its development tools
   require to function," and says such packages are "listed in `requirements.txt`
   (core dependencies) ... or `requirements-dev.txt`" — implying a runtime
   requirements file that no other document in the folder mentions.
   `dependency-management.md`'s own Repository Files Referenced table lists
   `pyproject.toml`, `requirements-dev.txt`, and `requirements-dev.lock`, but no
   plain `requirements.txt`.
7. **Which file installs the dev toolchain.** Related to the point above:
   `dependency-management.md`'s glossary entry for **Lock file** identifies it as
   `requirements-dev.lock`, and that page is explicit that contributors install
   "from `requirements-dev.lock`, not from `pyproject.toml` directly and not from
   `requirements-dev.txt` directly." `virtual-environments.rst`'s own Installing
   Dependencies section instead instructs `pip install -r requirements-dev.txt`
   directly and never mentions `requirements-dev.lock` anywhere in the page.
   Separately, `supported-python-versions.md`'s glossary spells the same concept
   **Lockfile** (one word) rather than `dependency-management.md`'s two-word
   **Lock file**, though the two definitions otherwise agree in substance.
8. **"Working tree" vs. "Local checkout."** `coding-style.md`'s glossary defines
   **Working tree** as "the checked-out copy of the repository on a contributor's
   machine, as opposed to the bare repository stored on the git host."
   `workstation-setup.md`'s glossary defines the same idea under a different
   name, **Local checkout** ("the copy of the repository you clone onto your own
   machine, as opposed to the shared copy on the remote"). Neither page's
   glossary cross-references the other's term, so the handbook carries two names
   for the same concept without saying which is canonical.
9. **A term only one glossary splits out.** `coding-style.md`'s glossary defines
   **Format pass** and **Lint pass** as a single run of the formatter or linter,
   terms that appear in no other document's glossary. Every other glossary that
   discusses these tools — `README.md`, `linting-and-formatting.md`,
   `onboarding-checklist.yaml`, `workstation-setup.md` — names only the tool
   itself ("Formatter," "Linter") and has no separate term for one run of it.
   In the same vein, `repository-layout.txt`'s glossary defines **Commit
   message** as the whole subject-plus-body unit but has no entry corresponding
   to `workstation-setup.md`'s more granular **Commit header** ("the first line
   of a commit message").

## Summary

The glossaries agree closely on the terms every page needs day to day —
formatter, linter, virtual environment, database file, loopback service,
draft pull request, editable install, pre-commit hook — usually word-for-word
in substance even when the exact phrasing varies. The disagreements cluster in
two places: numbers that a glossary entry states as fact (the line length
limit, the recommended and minimum Python versions, which linter the team
actually runs) and naming choices that were never reconciled between sibling
pages (topic vs. feature branch, working tree vs. local checkout, lock file vs.
lockfile). The sharpest single finding is `virtual-environments.rst`'s
**Dependency** glossary entry, which describes a runtime `requirements.txt`
that contradicts the zero-runtime-dependency premise stated as fact by
`dependency-management.md`, `README.md`, `coding-style.md`,
`supported-python-versions.md`, and `repository-layout.txt` alike.
