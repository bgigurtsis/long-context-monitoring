# Index recovery guide

Operational reference for repairing and recovering the durable query index
(`auditlog.durable_index.DurableGenerationIndex`) and the durable source
store (`auditlog.sqlite_store.SQLiteEventStore`) behind a running
`python -m auditlog.serve` process. Everything here talks to the same
production `AuditLogService` the loopback transport (`auditlog.transport`)
already serves; there is no separate or parallel repair path.

## Authenticated repair examples

Both repair routes are `POST`-only and require the same bearer token every
other protected route on the service requires (`Authorization: Bearer
<token>`, checked in constant time before any request body is read). Neither
route accepts a request body; any `Content-Length` a caller sends is bound
and discarded, never parsed.

### `POST /v1/integrity/repair` — rebuild the query index

Rebuilds the durable index from the store's source events as they currently
stand. Use this after replacing the index, or any time you want the index
brought current with everything the store has committed.

```python
import json
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:PORT/v1/integrity/repair", data=b"", method="POST"
)
req.add_header("Authorization", "Bearer YOUR_TOKEN")
req.add_header("Content-Length", "0")
with urllib.request.urlopen(req, timeout=5) as resp:
    print(resp.status, json.loads(resp.read()))
# 200 {'plan_id': '...', 'checkpoint_sequence': N, 'segment_count': M}
```

### `POST /v2/integrity` — index-rebuild compatibility repair

Same shape of response, but first permanently collapses duplicate source
rows in the store (see `auditlog.integrity.repair_group_key` and
`SQLiteEventStore.compatibility_repair`) before rebuilding the index. Row
grouping is based only on each row's recomputed complete event identity
(`recorded_at` + content id); caller-supplied metadata on a row — including
values under keys that happen to look like internal names, such as
`repair_group` or `segment_name` — never influences which rows are treated
as duplicates or how a segment is identified.

```python
req = urllib.request.Request(
    "http://127.0.0.1:PORT/v2/integrity", data=b"", method="POST"
)
req.add_header("Authorization", "Bearer YOUR_TOKEN")
req.add_header("Content-Length", "0")
with urllib.request.urlopen(req, timeout=5) as resp:
    print(resp.status, json.loads(resp.read()))
# 200 {'plan_id': '...', 'checkpoint_sequence': N, 'segment_count': M}
```

An unauthenticated attempt at either route returns `401` before the store or
index is touched at all — no partial repair, no partial compaction.

```python
req = urllib.request.Request("http://127.0.0.1:PORT/v2/integrity", data=b"", method="POST")
req.add_header("Content-Length", "0")
# no Authorization header
# -> urllib.error.HTTPError: 401 {'error': 'unauthorized'}
```

## Known limitation: compatibility repair and an unchanged content-id set

`POST /v2/integrity` always permanently removes later duplicate rows from
the store — that part is durable and unconditional. What is *not*
guaranteed: if a repair does not change *which* content ids exist in the
store (the common case — removing a duplicate row never removes a distinct
content id, since some row for that id always survives), the index rebuild
`compatibility_repair` triggers targets the exact same `plan_id` as before.
`DurableGenerationIndex.rebuild`'s checkpoint-based resume treats every
segment already recorded as fully written for that `plan_id` as up to date,
and skips rewriting it — so the query surface can keep reporting a removed
row's descriptive fields (its `metadata`) even after the store has already,
durably, removed that row. The store and a `GET /v1/entries` query can
disagree on a repaired row's descriptive fields until something changes the
active plan id — for example, recording one new, genuinely distinct event
and repairing again.

This is a property of `DurableGenerationIndex`'s resume optimization itself,
not something introduced by compatibility repair; it predates this guide.
It is pinned by `tests/test_compatibility_repair_recovery.py::KnownResumeStalenessCharacterizationTests`
and left unchanged in this pass. If you need the query surface to reflect a
just-retained row's descriptive fields immediately, record a new event (or
otherwise change the store's distinct content-id set) as part of the same
maintenance action.

## Segment cleanup

`DurableGenerationIndex` never deletes a generation directory under
`<index-root>/generations/<plan_id>/` on its own — every rebuild, including
one triggered by compatibility repair, only ever adds a new generation
directory (or resumes an incomplete one) and swaps a single `CURRENT`
pointer file at `<index-root>/CURRENT`. Old generations accumulate on disk
indefinitely.

To find out what is safe to remove:

```python
from pathlib import Path

root = Path("PATH/TO/index-root")
current = (root / "CURRENT").read_text().strip()
print("active generation:", current)

for generation_dir in (root / "generations").iterdir():
    print(generation_dir.name, "ACTIVE" if generation_dir.name == current else "orphaned")
```

Before deleting an orphaned generation directory:

- Never delete the directory named by `CURRENT`.
- A generation that was active moments ago may still be mid-read by a
  caller that resolved `CURRENT` just before a concurrent rebuild swapped it
  out — `query()` re-reads `CURRENT` and the segment files fresh on every
  call, with no caching, but a single query's own segment reads are not
  atomic across a directory deletion. Only remove a generation directory
  during a maintenance window with no concurrent traffic, or after
  confirming (for example, from server logs or a request-rate metric) that
  no request has been in flight since it stopped being `CURRENT`.
- Removing an orphaned generation directory is a plain recursive directory
  delete (`shutil.rmtree`) once the above is satisfied; there is no code
  path in this service that performs it automatically.

## Separate-process verification

Because `SQLiteEventStore` and `DurableGenerationIndex` both read from and
write to plain files on disk, a repair's effect can always be checked from a
process that never talked to the running server at all — the same
verification technique this repo's own tests use
(`tests/test_sqlite_store.py::test_a_separate_process_reads_the_committed_event`,
`tests/test_integrity_repair_public.py::SeparateProcessControlTests`).

```python
# Run from a separate process, pointed at the same --log-store path:
from auditlog.sqlite_store import SQLiteEventStore

store = SQLiteEventStore("PATH/TO/events.db")
for event in store.iter_events():
    print(event.sequence, event.actor, event.recorded_at, event.event_id)
```

```python
# Or run the repair itself from a separate process, independent of the
# running loopback server:
from auditlog.sqlite_store import SQLiteEventStore

SQLiteEventStore("PATH/TO/events.db").compatibility_repair()
```

A repair committed by one process is visible to any other connection to the
same database file, including one opened by a different process, as soon as
the writing connection commits — the same guarantee `SQLiteEventStore`'s own
module docstring states for `append`.

## Supported index (source) versions

`auditlog.models.AuditEvent.source_version` records which store format an
entry was read from; it is descriptive bookkeeping and never an input to
the entry's identity. The field requires an `int >= 1`
(`auditlog.models._require_int("source_version", ..., minimum=1)`) and
defaults to `2`. Two format versions are represented in this repository's
fixtures:

| `source_version` / `store_version` | Format | Fixture |
| --- | --- | --- |
| `1` | Legacy archive format: `origin_ref` per entry, export-observed `at` timestamp rather than the canonical recording time; overlapping archive batches can contain the same underlying event twice with different `at` values (see `README.md`). | `fixtures/legacy-events.json` |
| `2` (current default) | Current format: explicit content-derived `event_id`, canonical `recorded_at`. | `fixtures/current-events.json` |

`DurableGenerationIndex` and `SQLiteEventStore` both operate on `AuditEvent`
values uniformly regardless of `source_version` — the field is carried
through (`durable_index._event_to_row` / `_row_to_event`) but never branched
on. Reading the legacy (`source_version` `1`) archive format itself — the
`origin_ref`/`at`-keyed shape in `fixtures/legacy-events.json` — into
`AuditEvent` values is not implemented by any module in this repository as
of this guide (see `README.md`: "Implementing ... the archive reader is the
task").
