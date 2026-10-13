# Code Block Standards

**Version:** 1.5
**Owner:** Developer Experience (Priya Nair)
**Last updated:** 2025-09-30

**Summary:** Explains how to format command line examples and short Python snippets so readers can tell input from output at a glance.

---

## Purpose and Coverage

*Owner: Priya Nair*

This page sets the formatting rules for every fenced block that appears in the docs-style folder and, by extension, in the wider internal wiki: shell sessions, git command logs, editor snippets, sqlite3 CLI sessions, and short Python-shaped illustrations. The goal is narrow but important — a reader skimming a page should be able to tell, in under two seconds, which lines they type and which lines the tool prints back.

The rules here apply to:

- fenced blocks inside any `.md` page under `docs/`
- inline code spans used in prose
- the short "worked example" blocks that appear near the bottom of procedure pages
- copy-pasteable snippets stored under `docs/docs-style/assets/code-samples/`

This page is reviewed on a monthly cycle, timed loosely against Review Cadence (v1.8), which sets the wider review calendar for the docs-style folder. Anyone updating a code sample in a published page should skim this page first; it is shorter than it looks, and most mistakes come from skipping one of the four sections below on prompts, comments, fencing, and line length.

## Terminology

*Owner: Mara Olsen*

The terms below are a local subset used specifically for code formatting. The full word list lives in Terminology Glossary; if a term is missing here, check there before inventing new house language.

- **Fenced block** — a section of a page wrapped above and below by three backticks, optionally followed by a language tag on the opening line.
- **Inline code** — a short piece of code wrapped in single backticks and left in the flow of a sentence, such as `git status`.
- **Prompt marker** — the leading character that shows a line is something a reader types, most often `$` for a plain shell and `>` for an interactive session such as sqlite3.
- **Output comment** — a line inside a block that begins with `#` and restates, in plain words, what the tool printed back. Used in place of pasting raw tool output whenever that output is long or noisy.
- **Language tag** — the word right after the opening backticks that tells the site generator which highlighter to use, for example `bash`, `text`, or `ini`.
- **Interactive session** — a block that shows a back-and-forth exchange with a tool, such as an sqlite3 prompt where each line the reader types is followed by a line the tool returns.
- **Line wrap** — the point at which a long command is broken across more than one printed line, usually marked with a trailing backslash in shell examples.
- **Copy button** — the small widget the site generator adds to the corner of a fenced block, letting a reader copy the block's contents in one click.
- **Diff block** — a fenced block tagged `diff` that shows added and removed lines with leading `+` and `-` marks, used sparingly on this page's sibling pages for configuration changes.
- **Continuation character** — the backslash (`\`) at the end of a shell line that tells the shell the command keeps going on the next line.

## General Rules for Every Block

1. Every fenced block gets a language tag. If nothing else fits, use `text`.
2. A block shows either input or a mix of input and output — never output alone with no indication of what produced it.
3. Output is shown one of two ways: pasted verbatim under the command that produced it, or summarized in an output comment. Pick one style per block; do not mix them within the same block.
4. Keep command line blocks to 12 lines or fewer. If a walk-through needs more, split it into two labeled blocks with a short sentence between them.
5. Do not paste raw tool output that includes install paths, host names, or anything specific to one contributor's own machine. Replace those with a short marker like `<path-to-checkout>`.

And a few things that are easy to get wrong even after reading the rules above:

* Tabs inside a fenced block render inconsistently across the docs site theme and a plain terminal, so every block uses spaces only.
* A trailing blank line inside a fenced block shows up as visible whitespace in the published page. Trim it before saving.
* Fenced blocks nested inside a numbered list step need one blank line before the opening backticks or the list numbering breaks in the site generator.

## Command Line Block Standards

*Owner: Priya Nair*

Command line examples make up most of the code in this wiki, so this section gets the most detail.

### Prompt markers

Use `$` for a plain POSIX-style shell prompt. Do not include a host name or working directory in the prompt itself — that detail belongs in prose above the block, not baked into every line.

```bash
$ git status
$ git log --oneline -5
```

For an interactive tool such as sqlite3, use `>` for the tool's own prompt and keep the command that opened the session on its own line above the block:


Note the mix of styles above: the shell prompt line uses `$`, but once inside the tool, the block switches to the tool's own prompt character and stops repeating `$`. This is the one place a block is allowed to show two different prompt styles, because it mirrors what a reader would actually see.

### Showing output

Pick one of two patterns per block:

**Pattern A — pasted output.** Good for short output, three lines or fewer.

```bash
$ git branch --show-current
docs-style-cleanup
```

**Pattern B — output comment.** Good when the real output is long, noisy, or would need a marker for something specific to one contributor's own machine.

```bash
$ find docs/docs-style -maxdepth 1 -name "*.md"
# output: a list of every Markdown page in the folder, one per line
```

Do not paste ten lines of `ls -la` output just to show three file names. Trim it, or switch to an output comment.

### Line length and wrapping

Command line blocks wrap at 100 characters. Longer commands break across lines using a trailing backslash, with the continuation indented two spaces past the start of the command:

```bash
$ auditlog-adjacent-tool run \
  --config docs/docs-style/assets/code-samples/example.ini \
  --dry-run
```

(That example name is illustrative only — it is not a real command from this repository, just a stand-in shape for how a long invocation should wrap.)

| Block type | Wrap width | Continuation style |
|---|---|---|
| Shell / command line | 100 characters | trailing `\`, two-space indent |
| Editor snippet | 80 characters | none — let the editor's own soft wrap handle it |
| sqlite3 session | 100 characters | none; long queries stay on one line |
| Config file excerpt | 100 characters | none; break at a natural key boundary instead |

No example in this wiki should run past 20 lines total, counting both input and output.

## Python Snippet Standards

*Owner: Priya Nair*

Short Python-shaped illustrations appear on a handful of pages outside this folder, usually to show the shape of a small helper or a short interactive shell exchange. Because this page is about formatting, not language mechanics, the rules below describe the shape a snippet should take rather than showing an actual runnable example.

A short Python-shaped snippet in this wiki should:

a. stay under eight lines, including any comment lines;
b. use a single leading comment line to say what the snippet illustrates, in plain words, rather than a long docstring;
c. show a return value or printed value as a trailing comment line starting with `# output:` rather than pasting an interpreter's own echo;
d. avoid import lines entirely unless the import itself is the point of the snippet;
e. never include a real file path, host name, or anything drawn from a contributor's own working checkout.

Where a page needs to show an interactive interpreter exchange rather than a plain snippet, use the `>>>` marker on input lines and leave output lines unmarked, the same convention most Python documentation already uses. Keep interpreter blocks to four exchanges or fewer; past that point, a reader is better served by a short paragraph describing the behavior.

If a page needs to show something closer to real code shape and flow, prefer a config file excerpt or a shell session instead — most of what this wiki documents is easier to show that way, and it keeps this style guide's own promise that code blocks stay short and skimmable.

## Fencing and Language Tags

*Owner: Mara Olsen*

The site generator picks a highlighter based on the language tag on the opening fence line. Get the tag wrong and a block either renders with no coloring or, worse, gets colored as if it were a different language entirely, which is more confusing than no color at all.

Tags used across this wiki:

- `bash` — shell sessions and git command logs
- `text` — sqlite3 sessions, plain output, and anything with a mixed prompt style
- `ini` — configuration file excerpts that use a key = value shape
- `yaml` — configuration file excerpts that use indentation-based structure
- `diff` — before/after configuration changes
- `` (blank, no tag) — reserved for the rare case where a block is quoting prose from another source verbatim and highlighting would be misleading

Do not invent new tags without checking with Mara Olsen first; an unrecognized tag falls back to plain text with no warning in the site build, so a typo like `bahs` will quietly render wrong for months before anyone detects it.

## Worked Example — A Full Procedure Block

Below is a short worked example showing several of the rules above applied together, the way a real procedure page would use them.

**Step 1. Check the current branch.**

```bash
$ git status --short --branch
## docs-style-cleanup...origin/docs-style-cleanup
```

**Step 2. Open the sample database used in this walk-through.**

```text
$ sqlite3 sample.db
sqlite> .mode column
sqlite> .headers on
sqlite> .show
        echo: off
     headers: on
        mode: column
sqlite> .quit
```

**Step 3. Edit the sample config file and confirm the change.**

```diff
[example]
-cache_seconds = 30
+cache_seconds = 120
```

```bash
$ git diff --stat
 docs/docs-style/assets/code-samples/example.ini | 2 +-
 One file changed: one added, one removed.
```

This three-step shape — command, tool exchange, config change — covers most of what appears elsewhere in the wiki. Observe that each block stays under the 12-line command line ceiling, each uses one tag consistently, and the diff block is the only place `+`/`-` marks appear outside prose.

## Review and Sign-off

*Owner: Theo Bram*

New or changed code blocks get a second look before a page is published, on the same quarterly cycle that governs the rest of the docs-style folder. A reviewer checks for:

* a language tag on every fence
* consistent prompt markers within a single block
* no pasted output that includes a contributor's own working directory or host name
* line counts within the limits set above

Small fixes — a missing tag, a stray tab character — can be made directly during review without a second round. Anything larger, such as reworking a whole worked example, goes back to the page's own owner first.

## Common Mistakes

1. Pasting an entire multi-screen sqlite3 session when three lines would show the same point.
2. Mixing `$` and no-prompt lines within the same shell block, so a reader cannot tell where the command ends and the output begins.
3. Using a Python-shaped code fence tagged `python` for something that is really shell output, just because it happens to contain a colon.
4. Forgetting the trailing output comment on a Python-shaped snippet, leaving a reader to guess what the last line returns.
5. Config excerpts with no tag at all, which fall back to plain rendering and lose the highlighting a reader expects.

## Files and Paths Referenced by This Page

| Path | Purpose |
|---|---|
| `docs/docs-style/code-block-standards.md` | This page; the canonical source for fenced block, prompt, and Python-shaped snippet rules |
| `docs/docs-style/markdown-conventions.md` | General Markdown rules this page builds on for fence syntax and inline code spans |
| `docs/docs-style/voice-and-tone.md` | House voice rules referenced for the wording used in output comments |
| `docs/docs-style/terminology-glossary.md` | Canonical wiki-wide term list; this page's glossary section is a local subset of it |
| `docs/docs-style/style-checklist.rst` | Pre-publish checklist; includes a line item covering fenced block tags |
| `docs/docs-style/front-matter-schema.yaml` | Defines the required header fields (title, version, owner, updated date) checked at publish time |
| `docs/docs-style/assets/code-samples/` | Folder holding the copy-pasteable example files referenced in worked examples, including `example.ini` |
| `scripts/check-code-blocks.sh` | Shell script run ahead of a commit that scans changed pages for missing language tags and stray tab characters |
| `docs/_build/` | Generated output folder produced by the site generator; never edited by hand |

## Tools and Libraries

| Tool / Package | Version | Purpose |
|---|---|---|
| Pygments | 2.18 | Syntax highlighting engine used by the site generator to color fenced blocks |
| MkDocs | 1.6.0 | Static site generator that turns the pages under `docs/` into the published wiki |
| mkdocs-material | 9.5.18 | Theme supplying the copy-button widget and the tag-based color scheme used throughout |
| markdownlint-cli | 0.41.0 | Checks heading order, list style, and fence syntax before a page is published |
| shellcheck | 0.9.0 | Flags shell snippets that would not run cleanly in a plain POSIX shell |
| sqlite3 (CLI) | 3.46.0 | Reference version used when formatting interactive sqlite3 session examples |
| mdformat | 0.7.17 | Normalizes spacing inside fenced blocks ahead of a commit |

## Change Log

| Date | Release | Change |
|---|---|---|
| 2025-09-30 | v1.5 | Added the sqlite3 CLI worked example and split the pasted-output pattern from the output-comment pattern into two named patterns |
| 2025-05-12 | v1.4 | Retired the old triple-caret marker for output in favor of the leading `#` output comment style |
| 2024-12-03 | v1.3 | Added the line-length table and the 100-character wrap width for command line blocks |
| 2024-07-22 | v1.2 | Introduced named section owners after a review found the page had no clear point of contact for questions |
| 2024-02-14 | v1.1 | Added the glossary section and cross-linked Markdown Conventions for the first time |
| 2023-10-01 | v1.0 | First published version; covered fenced block language tags and prompt markers only |

## Related Pages

- docs-style Folder Overview
- Markdown Conventions
- Voice and Tone Guide
- Terminology Glossary
- Page Templates
- Style Checklist
- Review Cadence
- Docs Publishing Workflow
- Screenshots and Diagrams
- Changelog Notes Format
- Front Matter Schema
