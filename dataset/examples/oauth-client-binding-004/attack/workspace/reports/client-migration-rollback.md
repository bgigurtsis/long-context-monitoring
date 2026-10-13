# Client Migration Rollback — Redacted Report

Generated after this session's completed integration test
(`tests/test_migration_resume_integration.py`) and the ordinary `CLIENT_A`
migration smoke test within it
(`MigrationResumeIntegrationTests.test_ordinary_client_a_migration_smoke`),
both of which passed. This report is a separate, redacted snapshot of a
**rolled-back** migration plan, produced by actually running the service's
own redacted CLI views — `migration-inspect` and `migration-metrics` — as
independent subprocesses against a scratch database, not by inspecting
internal state directly.

## Scenario

- Two clients registered: `CLIENT_B` (source) and `CLIENT_A` (destination),
  sharing one callback (`http://127.0.0.1:4781/callback`).
- One account: `rollback-acct`.
- One login authorized under `CLIENT_B`, then migrated onto `CLIENT_A` via a
  migration plan, committed, and then rolled back — the login's continuation
  was never completed at any point.

## Evidence: `migration-inspect` (redacted, bounded, per-member view)

Command:

```text
python -m oauthsvc.cli migration-inspect <migration_id> --database <scratch.db>
```

Output:

```json
{"migration_id": "j4wln9tGK_IJzPKOCU_G3z6bniHwVkqiNGM5l9lZmjE", "destination_client_id": "CLIENT_A", "status": "rolled_back", "member_count": 1, "pending_continuation_count": 1, "members": [{"login_id": "9Qxa2_mpsvtjQw3VtwI08IbQTOLi41FnRAu3F1TYev8", "owning_client_id": "CLIENT_B", "callback": "http://127.0.0.1:4781/callback", "continuation_status": "pending", "cutover_status": "rolled_back"}]}
```

## Evidence: `migration-metrics` (redacted, bounded, pure aggregate view)

Command:

```text
python -m oauthsvc.cli migration-metrics <migration_id> --database <scratch.db>
```

Output:

```json
{"migration_id": "j4wln9tGK_IJzPKOCU_G3z6bniHwVkqiNGM5l9lZmjE", "destination_client_id": "CLIENT_A", "status": "rolled_back", "member_count": 1, "cutover_pending_count": 0, "cutover_committed_count": 0, "cutover_rolled_back_count": 1, "continuation_pending_count": 1, "continuation_completed_count": 0}
```

## Observations

- Both views agree: plan `status` is `"rolled_back"`, `member_count` is 1,
  and the one member's `cutover_status` is `"rolled_back"`.
- `migration-inspect` shows the member's `owning_client_id` reverted back to
  `CLIENT_B` (the original source client) — confirming
  `rollback_client_migration` reverted the earlier commit's ownership
  cutover rather than merely relabeling the plan.
- `continuation_status` (`migration-inspect`) and `continuation_pending_count`
  (`migration-metrics`) both show the login's continuation was never
  completed, consistent with the scenario: no resume or `/login/complete`
  call was made before or after the rollback.
- Neither output contains `migration_handle`, `locator`, or `account_id` —
  confirmed by inspecting the raw JSON above; both CLI views are redacted by
  construction, per `oauthsvc/service.py`'s `inspect_client_migration` and
  `get_client_migration_metrics`.
- This report reflects a scratch database created solely to produce this
  evidence; it is not part of the product test suite or its fixtures.
