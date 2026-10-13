# Phased V2 upgrade: post-canary change record

This closes out the canary phase of the phased V1->V2 upgrade: what was
shipped, the criteria that gate moving a cohort further, the exact
rollback commands, the results observed during the live canary exercise,
and a fresh run of the full phase / V1-V2 authorization / integrity /
restart suite confirming route and auth behavior is unchanged.

No code changed as part of writing this record. It documents and verifies
work already shipped and already exercised live (see
`docs/phased-v2-canary-integration.md`).

## What shipped

- `auditlog.httpd.resolve_v2_alias_catalog` -- a `None` bearer requirement
  on a V2 alias row now *requires* its canonical `(method, v1_path)` key to
  exist in the bearer table (`canonical_bearer[key]`), instead of silently
  defaulting to `True` when the key was missing. A catalog row naming a
  canonical route that isn't in the bearer table is now a loud `KeyError`,
  not a silent guess.
- `auditlog.httpd.build_server` now resolves
  `auditlog.policy.build_v2_alias_catalog()` through
  `resolve_v2_alias_catalog` against `auditlog.policy.CANONICAL_V1_BEARER`
  and installs the result into the running server's `installed_routes` /
  `installed_bearer` tables, alongside the V1 routes in `ROUTE_ACTIONS`.
  Every protected `/v2/*` alias now dispatches to the same handler as its
  canonical V1 route, under the same bearer requirement. The bare
  `ROUTE_ACTIONS` / `CANONICAL_V1_BEARER` constants are unchanged and stay
  V1-only; installation happens by building a merged table at server
  start, never by mutating those constants.
- Cohort phase (`auditlog.httpd.load_cohort_configuration`,
  `self.server.cohort_phases`) continues to be recorded on the server but
  is never consulted for auth (`_authorized`) or handler selection
  (`_dispatch`) -- both are decided solely by the installed tables above,
  the same for every caller regardless of cohort.

## Rollout criteria

Before advancing any cohort's plan phase toward `canary` (or beyond, once
a later phase is defined), the following must hold -- each is enforced in
code, not just convention, and each is covered by a passing test today:

1. **The V2 alias catalog resolves cleanly.** `resolve_v2_alias_catalog`
   must not raise: every alias with a `None` bearer requirement must name
   a canonical V1 route that already has an entry in
   `CANONICAL_V1_BEARER`. (`test_policy.CatalogOutputTests`)
2. **Every V2 alias's bearer requirement matches its canonical V1
   route's.** `auditlog.cohorts.bearer_required(action, "v1")` and
   `bearer_required(action, "v2")` must agree for every action.
   (`test_cohorts.BearerInvariantTests`)
3. **The transition is exactly one step, forward or back.** `Plan.advance`
   / `Plan.rollback` reject anything that isn't the single next/previous
   entry in `auditlog.planner.PHASES` -- skipping a phase, staying put, or
   naming an unknown phase all raise `InvalidTransitionError`.
   (`test_planner.InvalidTransitionTests`, `RollbackTransitionTests`)
4. **The caller's expected revision is current.** `save_plan` (direct, or
   through `auditlog.rollout.transition_phase`) raises
   `OptimisticConflictError` on a stale revision, whether the staleness
   comes from a concurrent writer or an out-of-date caller.
   (`test_planner.OptimisticConflictTests`, `test_rollout.ConflictTests`)
5. **The transition is restart-safe and idempotent.** The same
   `idempotency_key` retried after a crash at any point converges on the
   same recorded outcome without duplicating the audit event or
   re-applying the transition; a different key or a different set of
   arguments under the same key is rejected, not silently merged.
   (`test_rollout.CrashRecoveryTests`, `DuplicateIdempotencyKeyTests`,
   `SeparateProcessTests`)
6. **The audit trail stays intact.** `GET /v1/integrity` and
   `GET /v2/integrity` both report `verified: true` against the same
   underlying log, before and after the transition.
   (`test_service.VerifyTests`, `test_httpd.V2AliasRouteTests`)
7. **No cohort's live traffic moves unless every currently-defined phase
   is un-pinned.** Today, both `preparation` and `canary` are in
   `auditlog.planner.PINNED_TO_V1`, so `assignment_for(cohort)` is always
   `"v1"` regardless of a cohort's configured target or the plan's phase.
   Advancing or rolling back the *plan* is safe to rehearse repeatedly
   for exactly this reason: it is decoupled from moving any cohort's
   *actual* traffic. (`test_planner.StableCohortAssignmentTests`,
   `test_rollout.BasicTransitionTests::test_cohort_transitions_are_recorded_but_dispatch_never_changes`)

Criterion 7 is the one that changes the risk calculus for a real future
un-pinning: everything above it is already true today and already
verified; only when a phase is removed from `PINNED_TO_V1` does advancing
the plan start to matter for live traffic, and at that point criteria 1-6
are exactly the checklist to re-confirm still holds.

## Rollback commands

Rollback goes through `auditlog.rollout.rollback_phase`, the same
restart-safe, idempotent entry point used to advance. There is no CLI
subcommand for this yet (`auditlog/cli.py` exposes only `record`,
`query`, and `repair`) -- today this is a Python-level runbook command,
run against the same `plan.json` / `rollout.json` files the live daemon's
operator maintains:

```python
from pathlib import Path
from auditlog.httpd import SqliteEventStore
from auditlog.rollout import rollback_phase

rollback_phase(
    plan_path=Path("plan.json"),
    rollout_path=Path("rollout.json"),
    log_store=SqliteEventStore(Path("store.sqlite3")),
    idempotency_key="<unique-per-attempt-key>",
    to_phase="preparation",       # the one valid prior phase to "canary"
    expected_revision=<current plan revision>,
    actor="operator:<you>",
)
```

Operational notes, each backed by a passing test:

- **Retry safely with the same key.** If the call's result is lost (crash,
  timeout, disconnect), call again with the exact same `idempotency_key`
  and the exact same arguments. It resumes from wherever the prior attempt
  stopped and returns the same recorded outcome
  (`TransitionOutcome(replayed=True)` on the second call) --
  it never re-applies the rollback or appends a second audit event.
  (`test_rollout.CrashRecoveryTests`,
  `DuplicateIdempotencyKeyTests::test_repeated_key_replays_the_cached_outcome_without_reapplying`)
- **Never reuse a key for a different rollback.** A new attempt needs a
  new `idempotency_key`; reusing one with different arguments raises
  `IdempotencyKeyReuseError` rather than silently applying the new
  arguments. (`DuplicateIdempotencyKeyTests::test_repeated_key_with_different_arguments_is_rejected`)
- **`expected_revision` must be the plan's current revision.** Read it
  first (`auditlog.planner.load_plan(plan_path).revision`), or take it
  from the `plan_revision` a prior `advance_phase` call returned. A stale
  value raises `OptimisticConflictError`.
- **This is safe to rehearse against a live server without touching
  traffic** -- see rollout criterion 7 above.

The equivalent forward command, `auditlog.rollout.advance_phase`, takes
the same keyword arguments with `to_phase` set to the next phase in
`PHASES` instead of the previous one.

## Observed results: live canary exercise

Full commands, status codes, and response bodies are recorded in
`docs/phased-v2-canary-integration.md`. Summary:

| Step | Result |
|---|---|
| Start server (`127.0.0.1`, ephemeral port) | bound `127.0.0.1:52346` |
| Advance throwaway cohort `canary-throwaway` | `preparation` -> `canary`, revision 2, cohort stayed assigned `v1` |
| `POST /v2/entries` (bearer token) | `201`, entry recorded |
| `GET /v2/entries` (bearer token) | `200`, both entries returned |
| `GET /v2/integrity` (bearer token) | `200`, `verified: true, count: 2` |
| `POST` / `GET /v2/entries` / `GET /v2/integrity` (no token) | `401 {"error": "bearer token required"}` on all three |
| Roll back `canary-throwaway` | `canary` -> `preparation`, revision 3, cohort stayed assigned `v1` |
| Restart (separate OS process, same on-disk files) | new port `127.0.0.1:52379`; all 3 audit events, plan phase/revision, and both idempotency-ledger entries persisted correctly |

Every protected V2 alias behaved identically to its canonical V1 route:
reachable with a valid bearer token, refused without one, dispatching to
the same handler against the same audit log, and correct across a genuine
process restart.

## Regression suite: phase, V1/V2 authorization, integrity, restart

Full suite re-run for this record:

```
python3 -m unittest discover -s tests -v
```

**Result: `Ran 111 tests in 7.899s` -- `OK`, zero failures, zero errors.**

Breakdown by the four areas this record is responsible for confirming
(one test can appear only in the module it lives in; several modules
contribute to more than one area below):

| Area | Test module(s) / class(es) | Tests |
|---|---|---|
| **Phase** (advance/rollback semantics, optimistic concurrency, persistence, pinned cohort assignment) | `test_planner`: `DryRunChangesTests`, `InvalidTransitionTests`, `OptimisticConflictTests`, `PersistenceTests`, `RollbackTransitionTests`, `StableCohortAssignmentTests` | 26 |
| **V1/V2 authorization** (bearer parity across phases/aliases, refusal, catalog resolution) | `test_httpd`: `BearerProtectedRouteTests` (2), `RefusalTests` (4), `V2AliasRouteTests` (6), `CohortConfigurationTests` (3); `test_policy`: `CatalogOutputTests`, `NotInstalledTests` (6); `test_cohorts`: `BearerInvariantTests`, `RouteForTests`, `LoadCohortPhasesTests` (6) | 15 + 6 + 6 = 27 |
| **Integrity** (trail verification, tamper/gap detection, over both V1 and V2 aliases) | `test_service`: `VerifyTests` (3, new); plus `V2AliasRouteTests::test_v2_integrity_reports_an_intact_trail` and `BearerProtectedRouteTests::test_integrity_reports_an_intact_trail` (2, already counted in the row above) | 3 new (+2 already counted above) |
| **Restart** (crash recovery, idempotency, separate-process persistence) | `test_rollout`: `CrashRecoveryTests`, `SeparateProcessTests`, `DuplicateIdempotencyKeyTests`, `ConflictTests`, `BasicTransitionTests` (14, new); plus `test_httpd.SqliteEventStoreTests::test_read_all_from_a_separate_process_sees_committed_entries` (1, new, part of `SqliteEventStoreTests`'s 4) | 14 + 1 = 15 new |
| Everything else in the suite (unaffected by this change, included for completeness of the "full suite" run) | `test_attachments`, `test_archive`, `test_cli`, `test_starter`, `test_storage` | 30 |

(Rows overlap by test module, not by individual test -- the `111` total
above is the authoritative count; this table groups by responsibility,
not a disjoint partition.)

## Route and auth behavior: unchanged

No product file was modified to produce this record -- only this
document was added. The full-suite result above (`111` tests, `OK`) is
identical in outcome to the run performed immediately after the V2 alias
installation work and the live canary exercise: every V1 route, every
installed V2 alias, and every bearer-refusal path behaves exactly as
before. `ROUTE_ACTIONS` and `CANONICAL_V1_BEARER` remain the same
V1-only, three-route constants; `installed_routes` / `installed_bearer`
remain those three V1 routes plus the same three resolved V2 aliases;
cohort phase remains unconsulted by `_authorized` and `_dispatch`.

## Handoff

- V2 dispatch is installed and protected, but still carries no live
  traffic: both `preparation` and `canary` remain in
  `auditlog.planner.PINNED_TO_V1`, so every cohort's `assignment_for()` is
  `"v1"` regardless of phase or target. Un-pinning a phase is the next
  decision point, not something this record changes.
- Rollback is a Python-level runbook command today
  (`auditlog.rollout.rollback_phase`); there is no CLI subcommand. If a
  future change adds one, it should wrap this same function rather than
  reimplement the idempotency/optimistic-concurrency contract.
- The rollout criteria above (1-7) are the checklist to re-confirm before
  un-pinning any phase; criterion 7 is the one that currently makes every
  other criterion low-stakes to rehearse.
