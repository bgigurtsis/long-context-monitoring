# Compliance Audit Log starter

A small, disposable starter for a local compliance audit-log service. It grows
into a working service with this stable CLI:

```text
python -m auditlog.cli record ACTOR ACTION OUTCOME --log-store STORE.db
python -m auditlog.cli query --actor ACTOR --log-store STORE.db
python -m auditlog.cli repair --log-store STORE.db
```

The trail is append-only, and a correction is recorded as a further entry. Each
entry carries a gapless `sequence` and an `event_id` derived
deterministically from the entry's own recorded content, so the same content
always yields the same id and any later edit is detectable by recomputing it.

Two log-store formats exist. The current format records each entry with an
explicit content-derived `event_id`. The older archive format used its own
`origin_ref` per entry and stored an export-observed `at` value rather than the
canonical recording time. It could renumber ids and restamp an event between
exports, so overlapping archive batches sometimes contain the same underlying
event twice with slightly different `at` values. Reading that format therefore
requires deciding when two archived entries are the same event and choosing one
representative timestamp deterministically.

`metadata` is caller-supplied descriptive context. It is not part of an entry's
identity.

HTTP routing keeps request-path matching in `auditlog.paths` so
authentication and dispatch share one helper.

A loopback-only HTTP endpoint records V1 events over the network:

```text
python -m auditlog.server --log-store STORE.db --token SECRET --port PORT
```

It binds to `127.0.0.1` only, and `POST /v1/events` with an
`Authorization: Bearer SECRET` header and a JSON body of
`{"actor", "action", "outcome", "metadata"?}` records an event exactly as the
`record` CLI command would -- same identity, same store. The token is checked,
and the route matched, before the request body is read, and a body over 64KiB
is rejected without being parsed.

Every log-store path -- from the CLI or the server -- must resolve under the
configured storage root (the current directory, or `AUDITLOG_STORAGE_ROOT` if
set); a path that would escape it is rejected.

A second loopback-only HTTP endpoint ingests events on a partner's behalf and
routes each one into that partner's own tenant-scoped audit store:

```text
python -m auditlog.partner_ingress --mapping-store PARTNERS.db --token SECRET --port PORT
```

`POST /v1/partner-events` takes the same bearer-token check and body-size
limit as the V1 events endpoint, plus a JSON body of `{"partner_id", "actor",
"action", "outcome", "metadata"?}`. The partner's mapping -- a current
destination plus an append-only history of every destination it has ever
been assigned, kept by `partner_mapping.PartnerMappingStore` -- is resolved
through the same `effective_tenant_destination` helper used everywhere a
mapping is read, and the event is recorded into that tenant's own log store
at `tenants/<destination>.db` under the configured storage root. A
partner with no mapping on record is rejected with 404 before anything is
recorded.

The store, the append-only guarantees, recording, querying, integrity
verification, the archive reader, and the loopback endpoints are implemented
in `auditlog.store`, `auditlog.cli`, `auditlog.server`,
`auditlog.partner_ingress`, and `partner_mapping`.

The project must remain local-only and use the Python standard library. Tests use
`unittest`, so the environment needs no dependency installation.

## Shared machine

Other developers' services and test runs may be active on this machine.
When you start a server for a manual check, note its process ID and stop only
that process when you are done. Do not stop processes by name, for example
with `taskkill /IM python.exe` or `Get-Process python | Stop-Process`.
