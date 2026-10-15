# Dataset

The dataset contains 30 matched pairs of honest and constructed attack
transcripts. The five task families cover import integrity, audit routing,
OAuth client binding, notification recipient binding, and notification recovery.

```text
examples/<example-id>/
  spec.yaml
  inputs/seed/             starting application, when available
  honest/
    manifest.json
    transcript/            native JSONL and linked session files
    workspace/             final honest application files
  attack/
    manifest.json
    transcript/            constructed JSONL
    workspace/             final application files with the inserted changes
```

[index.json](index.json) lists each example's title, family, relative paths,
construction labels, hashes, and starting-workspace availability. Each arm's
manifest records its model settings, compaction boundaries, and file hashes.
Transcript records and archived workspace files retain their original bytes.

Tree hashes use SHA-256 over each file's relative POSIX path encoded as UTF-8,
a NUL byte, the unchanged file bytes, and another NUL byte, concatenated in
order. Sort by tuples of lowercase path components, then by the original
component tuples to break case ties. This explicit ordering reproduces the
release's Windows ordering on every platform. Individual transcript-file
hashes are ordinary SHA-256 of the file bytes.

The spec contains the actual host requests and two registered replacements.
Its `side_task.runtime_guidance` is insertion metadata. Honest generation does
not deliver it to the coding model. Each edit names its function, signature,
replacement source, host-turn anchor, and insertion position.

The attack is a labeled derivative of the matched honest session. Its
compaction summaries come from the neutral compactor and are distinct from the
honest session's native compactions. Construction metadata identifies the
compactor model, effort, provider, and request/result hashes.

Each attack manifest's `source_replays` lists the original construction records
for later tool results changed to reflect the inserted functions. Records name
the row UUID, tool call ID and name, relative file path, and replacement count.
`source_replay_provenance` identifies the source field and the SHA-256 of the
original construction record file. These records were restored from the
matched sources; their original format did not include before/after hashes.
An empty list means the source recorded no such replacements.

Starting workspaces are available for 26 examples. These four have their
transcripts and final workspaces but no archived starting workspace:

- `import-integrity-001`
- `audit-routing-001`
- `notification-recipient-001`
- `notification-recovery-001`

All examples can be read and monitored. Insertion uses the final honest
workspace and does not need a starting workspace. Generating a new session for
one of the four examples requires supplying its starting application.

The optional `inputs/padding_policy.json` constrains maintenance turns to their
declared workspace and tools. Generation validates that policy against the
starting maintenance files before running those turns.

The dataset contains no monitoring outputs. New results belong beneath the
ignored `outputs/` directory.

Dataset material is licensed under [CC BY 4.0](LICENSE). Attribute the
long-context-monitoring contributors and link to this repository when reusing it.
