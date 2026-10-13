# Replica failover and compatibility-repair runbook

Scope: promoting a replica after failover, and running compatibility repair
(`POST /v2/integrity`) against the durable SQLite journal it replayed into.
All commands below are real, reachable surfaces -- nothing here assumes
direct Python access to the service.

## 1. Promotion checks

Promotion (`AuditLogService.promote_replica`) and replay-after-promotion
(`auditlog.replay.replay_after_promotion`) are storage-service operations
only; there is no CLI subcommand or HTTP route for them. Run these checks
from the same process/script that holds the service object, before handing
the store file to a loopback server:

1. **Cursor exists and is where you expect.** `service.get_cursor(replica_id)`
   must be non-`None` once the replica has replayed anything, and its
   `offset` must equal the length of the source it was last replayed
   against. A `None` cursor after a replay call means the replica was never
   registered (`register_replica` was skipped) -- `replay_since_cursor`
   raises `KeyError` in that case, so this should not happen silently.
2. **The checksum was verified before promotion, not after.**
   `replay_after_promotion` raises `ChecksumMismatchError` and leaves the
   store untouched if the source's checksum does not match. Promote only
   after the pre-promotion tail replayed with a verified checksum.
3. **Promotion never rewrote an accepted event's identity.** After
   `promote_replica(replica_id, label)`, re-read the events the replica had
   already replayed (`list(service.events())`) and confirm their
   `event_id`/`identity` are unchanged from before promotion. Promotion is
   bookkeeping on the `replicas` row only; it must never touch the `events`
   table.
4. **The post-promotion tail resumes, not restarts.** Replaying the full
   source again after promotion (`replay_after_promotion` with the complete
   source) must report `applied` equal to only the new records past the
   cursor's prior offset, not the full source length. If `applied` equals
   the full source length, the cursor was not read correctly.

## 2. Authenticated repair examples

Start the production loopback server against the store the replica replayed
into:

```sh
python3 -m auditlog.serve \
    --log-store /path/to/audit.db \
    --bearer-token "$TOKEN" \
    --host 127.0.0.1 \
    --port 0
# prints: listening on 127.0.0.1:PORT
```

Run compatibility repair. The request body, if any, is never read by the
handler -- caller-supplied fields (including attempts to steer grouping,
e.g. `repair_group` or `replica_name`) have no effect on the result:

```sh
curl -s -X POST \
    -H "Authorization: Bearer $TOKEN" \
    "http://127.0.0.1:$PORT/v2/integrity"
# {"groups": 3, "retained": 3, "removed": 0}
```

A repair call that actually collapses legacy duplicates:

```sh
curl -s -X POST \
    -H "Authorization: Bearer $TOKEN" \
    "http://127.0.0.1:$PORT/v2/integrity"
# {"groups": 2, "retained": 2, "removed": 1}
```

An unauthenticated or wrongly-authenticated call is refused before anything
is touched:

```sh
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
    "http://127.0.0.1:$PORT/v2/integrity"
# 401

curl -s -o /dev/null -w '%{http_code}\n' -X POST \
    -H "Authorization: Bearer wrong-token" \
    "http://127.0.0.1:$PORT/v2/integrity"
# 401
```

Confirm the store is unchanged after a refused call by re-reading
`GET /v1/entries` with the correct token and comparing the entry count to
before the refused attempt.

## 3. Separate-process verification

Repair commits atomically to the SQLite file, not to any in-process state,
so its effect must be visible from a second, independent process reading
the same file -- this is the check that actually proves durability rather
than just trusting the response from the process that ran the repair.

1. Stop the server process that ran the repair (`SIGTERM`, then `SIGKILL` if
   it does not exit within a few seconds).
2. Start a new `python -m auditlog.serve` process against the same
   `--log-store` path (a different `--port` if run on the same host).
3. `GET /v1/entries` and `GET /v1/integrity` from the new process and
   compare, row for row, `sequence`, `actor`, `recorded_at`, and
   `content_id` against what the first process reported before it stopped.
   They must match exactly, and `all_verified` must be `true`.

`tests/test_integrity_repair_public.py` and
`tests/test_sqlite_store.py::SeparateProcessReadTests` automate exactly this
check; run them after any change to the repair or storage layer.

## 4. Known limits

- **`MAX_BODY_BYTES` (64 KiB) bounds every HTTP request body**, including
  `POST /v1/entries`. There is no HTTP replay endpoint, so this only limits
  how large a single recorded entry's metadata can be, not a replay batch.
- **`replay_since_cursor` / `replay_after_promotion` accept an unbounded
  number of source records per call.** Nothing in the storage layer caps
  batch size; a very large source is applied inside one transaction
  (`BEGIN IMMEDIATE` ... `COMMIT`), so an oversized batch is an
  all-or-nothing risk to transaction duration and lock hold time, not a
  partial-apply risk.
- **Promotion and replay are unreachable from the CLI or HTTP surface.**
  They exist only as `AuditLogService` methods; the only place to drive them
  is a script or process that imports the service directly, as in section 1
  above.
- **SQLite write-lock waits are bounded at 30 seconds** (`timeout=30` in
  `SQLiteAuditLogService._connect`). A repair or replay call contending with
  another writer for longer than that raises `sqlite3.OperationalError`
  rather than hanging indefinitely; the caller must retry, and no partial
  state is left behind either way (see `CompatibilityRepairCrashRecoveryTests`
  in `tests/test_sqlite_store.py`).
- **Compatibility repair is a permanent, one-way delete.** Collapsed
  duplicate rows are not recoverable after repair commits; there is no undo.
