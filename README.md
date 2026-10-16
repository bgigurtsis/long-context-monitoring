# Long-context monitoring

This repository contains a dataset of long coding-agent transcripts and tools
for generating honest sessions, inserting registered code changes, and
monitoring the resulting transcripts.

The dataset contains 30 matched honest and attack pairs. Each pair includes its
transcripts, final application files, host requests, and exact inserted
replacements. [The dataset guide](dataset/README.md) describes the files and
metadata.

## Install

Use Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked
uv run lcm --help
uv run pytest
```

On Windows, enable long paths for the clone if your checkout is nested deeply:

```bash
git clone -c core.longpaths=true https://github.com/bgigurtsis/long-context-monitoring.git
```

Generation also requires a logged-in Claude or Codex CLI. Monitoring and neutral
compaction use an API key supplied through the environment or a local ignored
`.env` file. OpenRouter uses `OPENROUTER_API_KEY`. The optional direct OpenAI
monitor backend uses `OPENAI_API_KEY`.

## Read and monitor a pair

Each example has an `honest/transcript/` and an `attack/transcript/` directory.
Passing the example directory to the monitor plans both arms.

```bash
uv run lcm monitor dataset/examples/import-integrity-002 \
  --strategy intervals --dry-run
uv run lcm monitor dataset/examples/import-integrity-002 \
  --strategy intervals --batch-name example
```

A dry run renders the prompts without making model calls or writing outputs.
Real monitoring writes beneath `outputs/`, which Git ignores. The default
estimated cost limit is $5. Model, effort, provider, visibility, and prompt
settings are configurable and recorded with each new result.

## Generate an honest session

A spec has four fields, `workspace`, `host_turns`, `compact_after`, and
`side_task`. Workspace paths are relative to the spec. The generator sends only
the host requests to the coding model. It archives the native transcript,
linked child sessions, model settings, compactions, and finished workspace.

```bash
uv run lcm generate --spec dataset/examples/import-integrity-002/spec.yaml \
  --backend claude --model claude-sonnet-5 \
  --generation-id 2026-10-14t1200z-example --dry-run
```

Remove `--dry-run` to generate the session. The output goes beneath
`outputs/generations/`. Use `--output-dir` to choose another destination.
The dataset guide identifies examples with available starting workspaces.

## Insert the registered changes

```bash
uv run lcm insert --spec dataset/examples/import-integrity-002/spec.yaml \
  --honest dataset/examples/import-integrity-002/honest \
  --output outputs/example-attack --dry-run
```

The dry run performs the same free consistency checks as construction, before
creating a model client. It can refuse archived histories that the current
validator cannot establish as consistent. Remove `--dry-run` to construct an
attack from a source that passes these checks. Insertion preserves the honest
source, checks each function signature, inserts complete Edit call/result
pairs, reconciles affected file reads, and rebuilds summaries with the neutral
compactor. It refuses to overwrite a destination or invent downstream tool
behavior that contradicts the inserted changes.

After an insertion, later native `Edit` or `Write` calls to the affected file
are refused, including edits that omit the function header. Shell commands
must match the supported grammar: one full-file `cat`, simple diagnostic or
Git inspection commands, or ordinary `python -m unittest`, `python -m pytest`,
and `pytest` invocations with basic verbosity flags. Compound commands,
redirection, glob expansion, scripts, and other shell programs are refused.
Choose another source or a later registered anchor for such histories. This
conservative check is an offline evidence check, not a shell sandbox or a proof
that arbitrary test code has no side effects.

Reconciliation updates only established reads of the affected current file.
Absolute paths require the native `cwd`; unrelated files, historical Git
output, and test output retain their original bytes. Partial or unrecognized
affected reads are refused. The stricter insertion rules do not change the
released transcripts or their availability for monitoring.

The anchors `before_host_turn`, `after_host_turn`, and
`after_native_function_edit` specify the insertion position. This is a
constructed transcript, with `manual_insertion: true` and
`policy_generation_evidence: false`. Its rebuilt summaries are neutral
compactor outputs. The honest session's compactions are native.

Generation and monitoring support Claude and Codex native records. Insertion
currently requires a Claude-shaped source transcript.

## Monitoring strategies

| Strategy | What it reads |
|---|---|
| `whole` | The complete visible trajectory, split only when the context budget requires it. |
| `intervals` | Each section between native compaction boundaries. |
| `summaries-only` | The compaction summaries. |
| `hierarchical-summary` | Summaries combined through a tree, followed by a final score. |
| `annotated-history` | Ordered sections with a carried record of relevant evidence. |
| `sandbox` | Transcript sections the monitor inspects through bounded tools. |
| `scratchpad` | Bounded transcript tools plus a private scratchpad. |

Tools-only visibility is the default. `--blind` withholds the objective catalog.
The [prompt guide](prompts/README.md) lists the released templates. Suspicion
scores describe the monitor's judgment; they do not establish whether the
application exhibits the registered behavior.

## Development and licenses

```bash
git config --local core.hooksPath .githooks
uv run python -m scripts.check_ruff
uv run pytest
```

Tests use local fixtures and mocked model clients. Code is licensed under
[MIT](LICENSE). Material under `dataset/` is licensed under
[CC BY 4.0](dataset/LICENSE).
