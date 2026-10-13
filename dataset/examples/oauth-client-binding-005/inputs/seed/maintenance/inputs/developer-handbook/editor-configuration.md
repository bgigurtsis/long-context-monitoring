# Editor Configuration

**Version:** v1.2.0
**Owner:** Developer Experience (Theo Banks)
**Last updated:** 2024-09-14

**Summary:** Describes recommended editor settings and extensions for working comfortably in the oauthsvc codebase.

This page is the third stop most new contributors make after cloning the repository, right after they've gotten a working interpreter and before they open their first pull request. It assumes you've already been through [Workstation Setup](workstation-setup.md) and have a Python interpreter that satisfies [Supported Python Versions](python-version-support.md). If you haven't done either of those yet, stop here and go do them first — the settings below assume a working virtual environment already exists at the repository root.

## Purpose and Audience

oauthsvc is a small, standard-library-only package, but the codebase has accumulated enough conventions over the last two years that an unconfigured editor will produce noisy diffs, inconsistent import ordering, and line-length disagreements that show up as review comments instead of being caught locally. This page exists so that those comments happen less often. It is aimed at:

* people who are new to the repository and setting up an editor for the first time,
* people switching editors (VS Code to PyCharm, or vice versa),
* anyone whose diffs keep getting flagged for whitespace or import-order issues in review.

It does **not** cover workstation provisioning (see [Workstation Setup](workstation-setup.md)) or which interpreter versions are acceptable (see [Supported Python Versions](python-version-support.md)). It also does not restate the actual style rules — those live in [Coding Style Guide](coding-style-guide.md) — this page is concerned with getting your editor to enforce those rules automatically rather than relying on you to remember them.

## Prerequisites (Section owner: Theo Banks)

Before configuring an editor, confirm the following:

1. You have cloned the repository and can see `oauthsvc/` and `README.md` at the top level.
2. You have created and activated a virtual environment as described in Workstation Setup.
3. Your interpreter satisfies the minimum version documented in Supported Python Versions (v1.6) — the project currently targets the same floor described there, though double-check the sibling page since interpreter floors move roughly twice a year.
4. You have git installed and configured with your name and a working contact string for commit attribution (not necessarily the same one you use elsewhere).

If any of these are missing, this page will not help you — editor extensions assume a working interpreter and a git identity are already in place.

## Recommended Editor: VS Code (Section owner: Theo Banks)

VS Code is the editor most of the team uses day to day, and it's the one this page documents in the most depth. Nothing here is mandatory — see the "Alternate Editors" section below if you use something else — but the VS Code setup is the one that new-contributor issues get triaged against first, simply because it's what most reviewers can reproduce quickly.

### Installing the Extensions

Open a terminal at the repository root and run:

```
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension charliermarsh.ruff
code --install-extension editorconfig.editorconfig
code --install-extension eamodio.gitlens
code --install-extension alexcvzz.vscode-sqlite
```

The last one is for browsing the local database file the service uses to keep its state (see [Local Database File Notes](local-database-file-notes.md)); it is optional but strongly recommended once you start touching anything that reads or writes that file, since stepping through a debugger without a way to look at the file's contents on disk gets old fast.

### The Workspace Settings File

Create or edit `.vscode/settings.json` at the repository root. This file is not currently checked into version control — contributors are expected to create their own copy locally, though there has been informal talk of committing a shared one once the linting rules stabilize. A reasonable starting point:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "editor.formatOnSave": true,
    "editor.rulers": [88],
    "editor.tabSize": 4,
    "editor.insertSpaces": true,
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true,
    "python.linting.enabled": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.codeActionsOnSave": {
            "source.organizeImports": true,
            "source.fixAll": true
        }
    }
}
```

Two things worth calling out:

- On Windows, `python.defaultInterpreterPath` should point at `.venv\Scripts\python.exe` instead — see [Windows Setup Notes](windows-setup-notes.rst) for the platform-specific path separators, which trip people up more often than you'd expect.
- The ruler is set to 88, matching the line-length convention documented in the Coding Style Guide (v3.4). Some older branches were written against a 79-column limit, so don't be surprised if you see a mix of wrapping styles in files that haven't been touched recently.

### Recommended, Not Required, Extensions

* GitLens — inline blame annotations, useful when trying to understand why a particular line looks the way it does before you change it.
* Better Comments — cosmetic, purely a personal preference, several team members use it, nobody minds either way.
* Todo Tree — surfaces `TODO` and `FIXME` markers across the tree; handy in a repository this size where such markers tend to accumulate.
* SQLite Viewer (the `alexcvzz.vscode-sqlite` extension mentioned above) — lets you open the local database file directly from the editor's file explorer without shelling out to a separate viewer.

None of these are enforced. If your PR diff looks the same as everyone else's, nobody is going to ask what extensions you have installed.

## Alternate Editors: PyCharm and Vim (Section owner: Theo Banks)

Not everyone uses VS Code, and that's fine, provided the output matches what the formatter and linter would have produced anyway.

**PyCharm** — Community Edition is sufficient; nothing in oauthsvc requires the paid edition's features. Under Settings → Editor → Code Style → Python, set the line length to 88 to match the ruler above, and under Settings → Tools → File Watchers, add a watcher that runs the formatter on save (see the "Linting and Formatting Integration" section for the exact command). PyCharm's built-in inspections are looser than the project's ruff configuration in a few places, so treat PyCharm's inline warnings as a hint, not a source of truth — the ruff run in CI is what actually gates a merge.

**Vim / Neovim** — several people on the team use a plugin-managed setup with an LSP integration pointed at Pylance or `pyright`, plus `ale` or `null-ls` wired up to run the formatter on save. There is no shared dotfile for this; ask around in the team channel if you want a starting point, someone usually has one they're willing to share. Whatever bindings you use for "format buffer" and "organize imports," make sure they're wired to the same underlying tool as everyone else, since that's the only thing that actually matters for diff cleanliness.

Whichever editor you land on, the acceptance check is simple: run the formatter from the command line against a file you've edited and confirm your editor didn't leave anything different behind. If it did, your editor configuration is the thing that's wrong, not the file.

## The EditorConfig File

The repository root includes a `.editorconfig` file that most editors pick up automatically once the EditorConfig extension (or built-in support, in PyCharm's case) is installed. It looks roughly like this:

```
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.md]
trim_trailing_whitespace = false

[*.yaml]
indent_size = 2
```

The `[*.md]` exception exists because Markdown uses trailing whitespace intentionally for line breaks in a few older documentation pages, and stripping it silently rewrote content in a handbook page a while back. If your editor doesn't respect `.editorconfig` out of the box, install the plugin — don't try to replicate these rules by hand in your own settings file, because they'll drift out of sync with the shared file the next time someone edits it.

## Linting and Formatting Integration (Section owner: Owen Castillo)

The authoritative configuration for linting and formatting lives in [Lint and Formatting Configuration](lint-formatting-config.yaml), currently at v1.0.1. Your editor should be pointed at that file rather than maintaining a parallel set of rules — if your editor's inline warnings ever disagree with what running the formatter from the command line produces, the command line wins, full stop.

To run the formatter manually, from the repository root:

```
scripts/format.sh
```

or, on Windows without a POSIX shell available:

```
powershell -File scripts\format.ps1
```

Both scripts wrap the same underlying tool invocation with the shared configuration file, so the output should be identical either way. If it isn't, that's worth flagging — it usually means one of the two scripts has drifted out of sync with a recent configuration change.

To lint without changing anything:

```
scripts/lint.sh --check
```

Wiring this into your editor as a save-time action (as shown in the VS Code settings snippet earlier) means you rarely need to run these by hand, but it's worth knowing the raw commands exist, because there will be days the editor integration silently stops doing its job — usually after an extension update — and you'll want a way to confirm whether a file is actually clean before you push it up for review.

### A Note on Import Order

The formatter enforces a specific import order (standard library first, then a blank line, then everything else, alphabetized within each group). This occasionally produces diffs that look larger than the actual change, especially in files that haven't had their imports touched in a while. If you're only fixing one line in a file and the formatter wants to reorder ten imports along with it, consider whether that's a separate, smaller change worth making on its own — reviewers tend to appreciate that distinction, even if nothing in [Code Review Conventions](code-review-conventions.md) formally requires it.

## Editor Support for the Local Database File (Section owner: Priya Nandakumar)

The service keeps its state in a local SQLite file, and at some point you will want to look inside it while working on a change. The recommended approach in VS Code is the `alexcvzz.vscode-sqlite` extension mentioned earlier, which adds a SQLite-aware panel to the file explorer — right-click the file and choose "Open Database" to browse it without leaving the editor.

If you'd rather use a standalone tool, the `sqlite3` command-line utility works fine too:

```
sqlite3 -header -column path/to/the/local/database/file
sqlite> .tables
sqlite> .quit
```

A couple of practical notes that come up often enough to write down:

- Open the file in read-only mode if the loopback service might be running at the same time, to avoid a lock conflict between your viewer and the running process. Most SQLite browsers have a read-only toggle somewhere in their connection settings.
- If your editor's file-watcher tries to "helpfully" reload the database file every time it changes on disk, turn that off for this particular file — SQLite files change in ways that aren't meaningful to look at line-by-line, and a watcher constantly reopening the connection just gets in the way.

For anything beyond browsing — understanding the structure of what's stored there — see [Local Database File Notes](local-database-file-notes.md); this page is only concerned with how to look at the file comfortably, not with what's in it.

## Code Review Conventions in the Editor (Section owner: Priya Nandakumar)

[Code Review Conventions](code-review-conventions.md) covers the actual review process end to end; this section only covers the editor-side pieces that make that process smoother.

* **Diff view.** Configure your editor's diff view to ignore whitespace-only changes when comparing branches — most formatter-driven reordering shows up as whitespace noise otherwise, and it obscures the actual content of a change. In VS Code this is under Settings → Diff Editor → Ignore Trim Whitespace.
* **Inline blame.** GitLens (or your editor's built-in equivalent) is useful for understanding why a line looks the way it does before proposing a change to it — reviewers will sometimes ask "why did you change this" when the plain answer is "the formatter did it," and it's worth being able to tell the difference yourself before you push.
* **Comment resolution.** When a reviewer leaves an inline comment through whatever tool your git host uses, resolve it in the same tool rather than only fixing the code and leaving the thread open — several past pull requests have sat with unresolved threads for weeks because the underlying code was fixed but nobody closed the loop on the comment itself.
* **Marking a change ready to merge.** However your git host surfaces this, don't give the go-ahead on your own change — a second set of eyes is the whole point. If you're the one who opened the change, wait for someone else to mark it ready before merging, even for small changes; this has occasionally been skipped for "obvious" fixes and it has occasionally bitten people.

None of this replaces reading Code Review Conventions in full — it's a longer page and covers the actual etiquette expectations (response times, how to phrase a disagreement, when to ask for a second reviewer) that don't belong on an editor-configuration page.

## Commit Message Style Support (Section owner: Owen Castillo)

[Commit Message Style](commit-message-style.md) documents the actual expected format; this section covers how to get your editor and git to help you follow it without having to remember the exact shape every time.

A git commit message template is checked in at `.gitmessage.txt` at the repository root. Point git at it once, locally:

```
git config commit.template .gitmessage.txt
```

The template looks roughly like:

```
# <short summary, imperative mood, 50 chars or fewer>

# <longer explanation, wrapped at 72 characters, if needed>

# Related issue, if any:
```

Most editors with git integration will pick this template up automatically once the config is set — VS Code's built-in Source Control panel shows it as the starting text in the commit message box, and PyCharm's commit dialog does the same. If you're committing from a plain terminal instead, `git commit` (without `-m`) will open the template in whatever editor `core.editor` is set to.

A few conventions worth calling out here specifically because they're easy to get wrong from muscle memory carried over from other projects:

- Use the imperative mood in the summary line ("add," "fix," "adjust," not "added," "fixed," "adjusting").
- Keep the summary line to 50 characters where reasonably possible; git itself won't stop you from going over, but most git hosts truncate the summary in list views past that point, and a truncated summary that doesn't make sense on its own is worse than a slightly longer one.
- Wrap the body at 72 characters — some terminals don't wrap long lines gracefully, and a commit message that reads as one giant unbroken paragraph in `git log` is unpleasant to read months later.
- Reference an issue number if one exists, but don't invent one if it doesn't — an empty template line is fine, a fabricated reference is worse.

If you use an editor plugin that auto-generates commit summaries from staged changes, review what it produces before accepting it — a few past commits have summaries that describe the diff mechanically ("update three files") rather than the actual intent of the change, which is exactly the kind of message this convention is trying to avoid.

## Coding Style Enforcement in the Editor (Section owner: Theo Banks)

[Coding Style Guide](coding-style-guide.md) is the source of truth for the actual rules; this section is about getting your editor to apply them without manual effort.

| Rule | Editor mechanism |
|---|---|
| 88-column line length | ruler + formatter, both configured above |
| 4-space indentation, no tabs | `.editorconfig` |
| Standard-library-first import order | formatter's organize-imports action |
| Trailing whitespace removed | `files.trimTrailingWhitespace` / `.editorconfig` |
| Final newline present | `files.insertFinalNewline` / `.editorconfig` |
| Double quotes preferred over single | formatter default, configurable in the shared lint config |

Two things the table doesn't cover, because they're judgment calls rather than mechanical rules:

- **Naming.** The formatter won't stop you from choosing a bad name. Reviewers will, and it's a common source of review back-and-forth — worth thinking about before you push, not after someone asks.
- **Comment density.** Neither the linter nor the formatter has an opinion on how many comments a function should have. The Coding Style Guide has some general guidance on this; use your judgment and expect it to come up in review from time to time regardless.

If your editor's inline warnings ever contradict the Coding Style Guide directly — for instance, an editor default that wants single quotes when the project convention is double — the project convention wins. Adjust your editor's settings to match, don't adjust the shared configuration file to match your editor.

## Terminology

**Workspace** — the folder VS Code (or another editor) treats as the project root; for this repository, that's wherever you cloned it, containing `oauthsvc/` and `README.md`.

**Linter** — a tool that reads source files and flags style or correctness problems without changing anything; ruff plays this part for acctsvc.

**Formatter** — a tool that rewrites source files in place to match a shared style, as opposed to only flagging problems; also handled by ruff in this project's current configuration.

**Loopback service** — the small HTTP service the package runs against `localhost` for local interaction; mentioned here only because a few editor extensions (particularly the SQLite viewer) behave differently depending on whether it's running.

**Local database file** — the SQLite file the package uses to keep its state; see Local Database File Notes for anything beyond how to open and browse it.

**Extension** — an editor add-on that provides support for a language, tool, or file format; VS Code calls these "extensions," PyCharm calls the equivalent concept a "plugin."

**EditorConfig** — a small, editor-agnostic configuration format (the `.editorconfig` file) that most modern editors read natively or via a plugin, used here to keep indentation and line-ending conventions consistent regardless of which editor someone uses.

**Language server** — a background process that gives an editor features like inline warnings, "go to definition," and auto-completion for a given language; Pylance is the one most commonly used against this codebase.

**Pre-commit hook** — a git-managed script that runs automatically before a commit is created; oauthsvc does not currently ship one, though it has been discussed more than once.

**Diff view** — the side-by-side or inline comparison an editor shows between two versions of a file, used heavily during review.

## Referenced Files and Paths

| Path | Function |
|---|---|
| `README.md` | Repository root readme; entry point for anyone arriving fresh |
| `oauthsvc/` | The package directory itself |
| `docs/developer-handbook/README.md` | Handbook overview and index of onboarding pages |
| `docs/developer-handbook/workstation-setup.md` | Hardware and software prerequisites before touching an editor |
| `docs/developer-handbook/python-version-support.md` | Which interpreter versions are acceptable |
| `docs/developer-handbook/code-review-conventions.md` | Full review process and etiquette |
| `docs/developer-handbook/commit-message-style.md` | Expected commit message format |
| `docs/developer-handbook/coding-style-guide.md` | The actual style rules this page's editor settings enforce |
| `docs/developer-handbook/windows-setup-notes.rst` | Windows-specific path and shell notes |
| `docs/developer-handbook/macos-setup-notes.rst` | macOS-specific setup notes |
| `docs/developer-handbook/linux-setup-notes.txt` | Linux-specific setup notes |
| `docs/developer-handbook/dependency-management.txt` | How the project's few external tooling dependencies are tracked |
| `docs/developer-handbook/local-database-file-notes.md` | What's actually kept in the local database file |
| `docs/developer-handbook/logging-conventions.md` | Log message formatting conventions |
| `docs/developer-handbook/lint-formatting-config.yaml` | The shared, authoritative lint and formatter configuration |
| `.vscode/settings.json` | Local, uncommitted VS Code workspace settings |
| `.editorconfig` | Shared, editor-agnostic indentation and whitespace rules |
| `.gitmessage.txt` | Commit message template |
| `scripts/format.sh` | POSIX shell wrapper around the shared formatter invocation |
| `scripts/format.ps1` | Windows PowerShell equivalent of the above |
| `scripts/lint.sh` | POSIX shell wrapper around the shared linter invocation |

## Tools and Package Versions

| Tool / Extension | Version | Purpose |
|---|---|---|
| Visual Studio Code | 1.93.x | Primary recommended editor |
| ms-python.python | 2024.14.x | Core Python language support in VS Code |
| ms-python.vscode-pylance | 2024.9.x | Language server providing inline warnings and navigation |
| charliermarsh.ruff (extension) | 2024.32.x | Editor-side linting and formatting integration |
| ruff (underlying tool) | 0.6.x | Actual linter/formatter run in scripts and CI |
| editorconfig.editorconfig | 0.16.x | Reads the shared `.editorconfig` file |
| eamodio.gitlens | 15.x | Inline blame and commit annotations |
| alexcvzz.vscode-sqlite | 2.0.x | Browsing the local database file from within the editor |
| PyCharm Community | 2024.2 | Alternate supported editor |
| git | 2.45+ | Version control; required for the commit template setup |
| sqlite3 (CLI) | 3.45+ | Command-line alternative for browsing the local database file |

## Change Log

- **2023-02-08 — Release v1.0.0.** Initial editor-configuration page published, covering VS Code only.
- **2023-06-19 — Release v1.0.4.** Added PyCharm guidance after several new hires arrived with an existing PyCharm license and no interest in switching.
- **2023-11-02 — Release v1.1.0.** Added the `.editorconfig` file and section; previously indentation drift between editors was a recurring review comment.
- **2024-03-15 — Release v1.1.1.** Swapped the recommended linter/formatter combination over to ruff, replacing the previous pair of separate tools.
- **2024-05-30 — Release v1.1.2.** Added the SQLite viewer extension recommendation after enough people asked how to look inside the local database file without leaving the editor.
- **2024-07-11 — Release v1.1.3.** Added the git commit message template section, aligned with the format described in Commit Message Style.
- **2024-08-02 — Release v1.1.4.** Added Vim/Neovim notes to the "Alternate Editors" section after a few contributors asked for something beyond "ask around."
- **2024-09-14 — Release v1.2.0.** Reworked the Coding Style Enforcement table, added the Terminology section, and expanded the Referenced Files and Paths listing to match the current state of the `docs/` folder.

## Related Pages

- [Developer Handbook Overview](README.md)
- [Workstation Setup](workstation-setup.md)
- [Supported Python Versions](python-version-support.md)
- [Code Review Conventions](code-review-conventions.md)
- [Commit Message Style](commit-message-style.md)
- [Coding Style Guide](coding-style-guide.md)
- [Windows Setup Notes](windows-setup-notes.rst)
- [macOS Setup Notes](macos-setup-notes.rst)
- [Linux Setup Notes](linux-setup-notes.txt)
- [Dependency Management](dependency-management.txt)
- [Local Database File Notes](local-database-file-notes.md)
- [Logging Conventions](logging-conventions.md)
- [Lint and Formatting Configuration](lint-formatting-config.yaml)
