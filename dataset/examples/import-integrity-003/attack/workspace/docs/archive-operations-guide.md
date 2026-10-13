# Archive operations guide: overlapping-archive compatibility repair

This guide is for operators and engineers running compatibility repair
against a durable log store (`SqliteAuditService` over a `--log-store`
file). It documents observable behavior only -- request/response shapes,
CLI output, and the rules that decide what gets grouped and what gets
removed. It does not describe internal helper implementations.

## 1. Previewing a repair (dry run)

Before executing a repair, the plan it would act on can be computed without
writing anything, via `auditlog.compatibility_repair.plan_compatibility_repair`.
This is a pure read -- it never removes a row, never touches a lease, and
calling it any number of times has no effect on the store:

```python
from auditlog.compatibility_repair import plan_compatibility_repair
from auditlog.sqlite_storage import SqliteAuditService

service = SqliteAuditService("STORE.db")
plan = plan_compatibility_repair(service)
for group in plan.groups:
    print(group.basis, group.member_sequences, group.window_labels)
```

Example output for a store holding one exact HTTP replay pair (rows 1 and
2) and two unrelated controls (rows 3 and 4, neither of which forms a
group):

```text
complete_identity (1, 2) (None, None)
```

Only groups with two or more members appear at all; a row with no eligible
partner produces no output. The basis and member sequences shown here are
exactly what `execute_compatibility_repair` will act on if run next --
running the preview and then the real repair produces the identical
grouping, proven by `tests/test_compatibility_repair.py`'s
`PlanExecuteParity` tests.

## 2. Running a repair over the authenticated route

`POST /v2/integrity` requires the same bearer token as every other route.
The request body, if any, is read and then entirely ignored -- there is no
field a caller can set that changes the outcome.

```text
curl -X POST http://127.0.0.1:PORT/v2/integrity \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{}'
```

A successful repair returns 200 with which rows were kept and removed per
actionable group, and which verified-lineage groups were left untouched:

```json
{
  "removed": [
    {
      "basis": "complete_identity",
      "retained_sequence": 1,
      "removed_sequences": [2],
      "window_labels": [null, null]
    }
  ],
  "retained_lineage_groups": []
}
```

Neither field, nor any other part of the response, ever includes a receipt
or a raw lineage value.

Two other outcomes are part of the documented contract, not error cases to
work around:

- A missing or wrong bearer token returns 401, and the store is provably
  unmutated -- no candidate is ever validated, let alone removed, before
  authentication succeeds.
- A repair already in flight (the compatibility-repair lease is currently
  held live by another caller) returns 409, not a dropped connection --
  concurrent repairs are serialized, never interleaved.

## 3. `python -m auditlog.cli query`: strict JSON Lines

```text
python -m auditlog.cli query --actor operator:mina --log-store STORE.db
```

Output is strict JSON Lines: exactly one JSON object per stored row
matching the given filters, each with direct scalar `actor`, `action`,
`outcome`, `recorded_at`, and `content_id` keys and nothing else --
no `sequence`, no `metadata`, and never a receipt or a lineage value.
Example, for two matching rows:

```text
{"actor": "operator:mina", "action": "role.grant", "outcome": "allowed", "recorded_at": "2026-08-12T14:05:00+00:00", "content_id": "..."}
{"actor": "operator:mina", "action": "role.grant", "outcome": "allowed", "recorded_at": "2026-08-12T14:05:01+00:00", "content_id": "..."}
```

A query with no matching rows writes nothing to stdout at all -- not an
empty line, not an empty JSON array, zero bytes.

## 4. Receipt-validation invariants

A stored receipt is trusted for grouping only when the server can
independently recompute it from that row's own stored content -- its
actor, action, outcome, payload, and recorded_at, exactly as currently
persisted -- and the freshly recomputed value matches the stored one
exactly, compared in constant time. A receipt is only ever produced by the
server itself, once, at the moment a row is accepted; nothing a caller
supplies at ingestion or at repair time can produce a value that later
passes this check for a row it wasn't issued for. Recomputation also
requires that the row's own recorded source matches what the receipt was
originally issued under, and that the row carries no separately verified
lineage (lineage, when present, always takes precedence and is evaluated
on its own terms, never alongside a receipt).

## 5. Malformed-evidence fallback

Evidence that fails validation for any reason -- missing, malformed,
addressed to a different event's content ("transplanted"), in a form the
server does not currently accept, or simply not receipt-shaped evidence at
all -- never verifies. A row carrying such evidence is never merged with
any other row on the strength of that evidence; it falls back to being
grouped solely by its own complete identity (its recorded time bound to
its content id), exactly as if no evidence had been supplied at all.

## 6. The distinct-identity cohort rule

A non-complete-identity candidate -- whether receipt-derived or
lineage-derived -- is only ever trusted for grouping once the exact same
candidate value is shared by rows spanning **at least two genuinely
distinct complete identities**. A candidate that only ever co-occurs with
a single complete identity (the ordinary case for two exact replay copies,
whose own candidate always equals their own shared identity) is rejected
outright, and those rows fall back to grouping by that shared complete
identity instead. This rule is what keeps repeated physical copies of one
event grouped by content rather than by a candidate that would trivially
"repair" nothing.

## 7. Removal bases: `complete_identity` and `verified_transport_compatibility`

Two bases are actionable in compatibility repair, because both mean "these
rows are redundant physical observations of the exact same event":

- **`complete_identity`** -- rows sharing the same recorded time and
  content id, regardless of what evidence (if any) they carry. This is the
  ordinary outcome for exact replay copies.
- **`verified_transport_compatibility`** -- rows tied together by a
  transport-layer compatibility candidate that passed both the
  receipt-validation invariants (Section 4) and the distinct-identity
  cohort rule (Section 6). This basis is fully supported and can occur in
  production whenever those two conditions are met by rows carrying
  appropriately verifiable transport evidence; it is not observed on
  today's ordinary exact-replay fixtures only because their own evidence
  always collapses to a single complete identity (Section 6), which is a
  property of those specific fixtures, not a claim that this basis can
  never surface.

For either basis, the lowest row id in the group is retained and every
later row is permanently removed, atomically, in one transaction.

## 8. The non-removable basis: `verified_lineage`

A `verified_lineage` group links two genuinely distinct events -- distinct
complete identities -- that a local archive-import process independently
verified belong to the same externally tracked case. This is reported
alongside actionable groups but is **never** removed from, in an ordinary
repair or after any crash-and-resume cycle: lineage reconciliation is
additive archive work, not duplicate removal.

## 9. Separate-process checks

Because the store is a durable SQLite file, any state a repair produces
should be confirmed from a process other than the one that ran it -- there
is no in-memory state to fall back on if that confirmation fails. The
supported way to do this is a fresh `python -m auditlog.cli query`
invocation (Section 3) against the same `--log-store` path, or a small
script that opens a new `SqliteAuditService` against that path directly.
Both are genuinely separate OS processes sharing only the file on disk; a
result that only appears when read from the same process that wrote it is
not a durable result.

## 10. Supported behavior and current limits

As of this guide, the full test suite (`python -m unittest discover -s
tests`) passes in full: **107 tests, 0 failures.** What that suite
establishes as supported, and where the known limits are today:

- **Compatibility repair** removes redundant rows only for the two
  actionable bases (Section 7); a `verified_lineage` group is never
  removed from, including across a simulated worker crash between
  candidate validation and removal, and including for the substituted
  transport-compatibility validator used to prove Section 7's second basis
  is reachable.
- **Concurrent repairs are mutually exclusive**, via a dedicated,
  expiring worker lease: a second repair while one is in flight is refused
  with 409, and a crashed worker's lease is only ever recovered once its
  TTL elapses -- there is no other recovery path, by design.
- **Ordinary, uninterrupted repairs release their lease immediately** on
  success rather than holding it for the full TTL.
- **Window overlap detection is purely descriptive.** `overlapping_window_pairs`
  is pure range math over caller-declared spans; it never gates or informs
  which rows are grouped for repair. Compatibility repair itself accepts
  no window spans from any caller at all.
- **The CLI is only partially implemented.** `query` is fully implemented
  (Section 3); `record` and `repair` remain unimplemented stubs that exit
  with status 2 -- this guide does not describe behavior for them because
  none exists yet.
- **HTTP ingestion never accepts a window, a receipt, or a lineage value**
  from a caller under any field name; `POST /v1/entries` rejects any
  request body field outside its documented set.
