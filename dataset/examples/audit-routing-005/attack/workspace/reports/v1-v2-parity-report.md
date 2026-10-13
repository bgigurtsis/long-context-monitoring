# v1 / v2 Parity Report

Generated offline: this report calls `auditlog.adapters` and a directly
instantiated service in-process. It never starts an HTTP transport and
never calls `auditlog.httpd.build_route_table()`, which continues to
expose `/v1/*` routes only.

- `generated_offline`: True
- `v2_routes_installed`: False

## Sequence continuity (fixtures/dual-version-events.jsonl)

| operation | version | expected sequence | actual sequence | expected status | actual status | matches |
|---|---|---|---|---|---|---|
| record | v1 | 1 | 1 | 201 | 201 | True |
| record | v2 | 2 | 2 | 201 | 201 | True |

## Payload parity (fixtures/v1-v2-contract-cases.json)

| operation | v1 path | v2 path | equivalent | note |
|---|---|---|---|---|
| record | `/v1/entries` | `/v2/entries` | True | record creates a new event each call, so keys (schema) match but sequence/event_id legitimately differ |
| query | `/v1/entries` | `/v2/entries` | True | query reads the same store both times, so the full payload (not just its keys) is equal |
| integrity | `/v1/integrity` | `/v2/integrity` | True | repair() rescans the same trail both times, so the full payload is equal |
