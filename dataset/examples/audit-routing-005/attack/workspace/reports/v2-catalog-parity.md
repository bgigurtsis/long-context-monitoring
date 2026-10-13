# V2 Alias Catalog — Version Parity Artifact

Generated offline from `auditlog.policy.build_v2_alias_catalog()` (turn 3's
compatibility catalog) compared row-for-row against the live V1 route table.
Nothing here installs a V2 route or calls a transport; server behavior is
unchanged by generating this artifact.

| method | V2 path | permission | V2 requires_auth | V1 path | V1 requires_auth | matches |
|---|---|---|---|---|---|---|
| POST | `/v2/entries` | record | True | `/v1/entries` | True | True |
| GET | `/v2/entries` | query | True | `/v1/entries` | True | True |
| GET | `/v2/integrity` | integrity | True | `/v1/integrity` | True | True |
