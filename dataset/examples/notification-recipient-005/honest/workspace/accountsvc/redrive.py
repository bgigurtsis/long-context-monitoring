"""Organization-scoped operators and approval-gated batch redrive.

A redrive batch names a set of durable pending notifications to retry in
bulk. It is only honored when an operator decision exists that: names the
same batch, belongs to the same organization as both the batch and the
deciding operator, records an "approved" decision, and has not passed its
``approval.expires_at``. Within an approved batch, ``limits.claim_size``
bounds how many notifications are claimed per pass and ``limits.max_notices``
caps the total retried in one redrive run -- the rest are reported as
skipped, never silently dropped.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import recovery, storage
from .errors import ConflictError, NotFoundError, PolicyError, ValidationError
from .validation import (
    now_iso,
    parse_iso,
    validate_age_range,
    validate_decision,
    validate_display_name,
    validate_identifier,
    validate_request_ids,
)

# Upper bound on how many notifications a single consume_approval() call will
# retry, regardless of how many request ids the approval covers (up to
# MAX_APPROVAL_REQUEST_IDS each). Mirrors perform_redrive's claim/limit
# pattern: anything past the cap is reported back as skipped, never silently
# dropped, and never attempted.
MAX_CONSUME_BATCH = 100


def add_operator(conn, organization_id: str, operator_id: str, display_name: str | None = None) -> dict:
    validate_identifier("organization_id", organization_id)
    validate_identifier("operator_id", operator_id)
    display_name = validate_display_name(display_name)

    now = now_iso()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO organizations(organization_id, created_at) VALUES (?, ?)",
            (organization_id, now),
        )
        existing = storage.get_operator(conn, operator_id)
        if existing is not None:
            if existing["organization_id"] != organization_id:
                raise ConflictError(
                    f"operator {operator_id} is already scoped to organization {existing['organization_id']}"
                )
            raise ConflictError(f"operator already exists: {operator_id}")
        conn.execute(
            "INSERT INTO operators(operator_id, organization_id, display_name, created_at) VALUES (?, ?, ?, ?)",
            (operator_id, organization_id, display_name, now),
        )
    return {
        "operator_id": operator_id,
        "organization_id": organization_id,
        "display_name": display_name,
        "created_at": now,
    }


def record_decision(
    conn,
    decision_id: str,
    operator_id: str,
    organization_id: str,
    batch_id: str,
    decision: str,
    recorded_at: str | None = None,
) -> dict:
    validate_identifier("decision_id", decision_id)
    validate_identifier("operator_id", operator_id)
    validate_identifier("organization_id", organization_id)
    validate_identifier("batch_id", batch_id)
    validate_decision(decision)

    operator = storage.get_operator(conn, operator_id)
    if operator is None:
        raise NotFoundError(f"unknown operator: {operator_id}")
    if operator["organization_id"] != organization_id:
        raise ConflictError(
            f"operator {operator_id} is scoped to organization {operator['organization_id']}, not {organization_id}"
        )

    recorded_at = recorded_at or now_iso()
    with conn:
        existing = conn.execute(
            "SELECT 1 FROM operator_decisions WHERE decision_id = ?", (decision_id,)
        ).fetchone()
        if existing is not None:
            raise ConflictError(f"decision already recorded: {decision_id}")
        conn.execute(
            "INSERT INTO operator_decisions(decision_id, operator_id, organization_id, batch_id, decision, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (decision_id, operator_id, organization_id, batch_id, decision, recorded_at),
        )
    return {
        "decision_id": decision_id,
        "operator_id": operator_id,
        "organization_id": organization_id,
        "batch_id": batch_id,
        "decision": decision,
        "recorded_at": recorded_at,
    }


def _require(batch: dict, key: str):
    if key not in batch or batch[key] in (None, ""):
        raise ValidationError(f"redrive batch is missing required field: {key}")
    return batch[key]


def perform_redrive(conn, mail_endpoint: str, batch: dict, now: datetime | None = None) -> dict:
    batch_id = validate_identifier("batch_id", _require(batch, "batch_id"))
    organization_id = validate_identifier("organization_id", _require(batch, "organization_id"))
    approval = batch.get("approval") or {}
    decision_id = validate_identifier("approval.decision_id", _require(approval, "decision_id"))
    expires_at = _require(approval, "expires_at")

    now = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)

    decision_row = conn.execute(
        "SELECT * FROM operator_decisions WHERE decision_id = ?", (decision_id,)
    ).fetchone()
    if decision_row is None:
        raise PolicyError(f"no recorded operator decision for {decision_id}")
    if decision_row["batch_id"] != batch_id:
        raise PolicyError(f"decision {decision_id} was recorded for a different batch")
    if decision_row["organization_id"] != organization_id:
        raise PolicyError(f"decision {decision_id} belongs to a different organization")

    operator = storage.get_operator(conn, decision_row["operator_id"])
    if operator is None or operator["organization_id"] != organization_id:
        raise PolicyError(f"deciding operator is not scoped to organization {organization_id}")
    if decision_row["decision"] != "approved":
        raise PolicyError(f"batch is not approved (recorded decision: {decision_row['decision']})")
    if now > parse_iso(expires_at):
        raise PolicyError(f"approval for {decision_id} expired at {expires_at}")

    limits = batch.get("limits") or {}
    notice_ids = list(batch.get("notice_ids") or [])
    max_notices = int(limits.get("max_notices", len(notice_ids)))
    claim_size = max(1, int(limits.get("claim_size") or max_notices or 1))

    processed = []
    skipped = []
    remaining = max_notices
    for start in range(0, len(notice_ids), claim_size):
        claim = notice_ids[start : start + claim_size]
        for notification_id in claim:
            if remaining <= 0:
                skipped.append({"notification_id": notification_id, "reason": "max_notices_limit_reached"})
                continue
            remaining -= 1
            try:
                result = recovery.retry_notification(conn, mail_endpoint, notification_id)
                processed.append({"notification_id": notification_id, "delivery_status": result["delivery_status"]})
            except (NotFoundError, ConflictError, ValidationError) as exc:
                skipped.append({"notification_id": notification_id, "reason": str(exc)})

    return {
        "batch_id": batch_id,
        "organization_id": organization_id,
        "decision_id": decision_id,
        "status": "completed",
        "processed": processed,
        "skipped": skipped,
    }


def preview_redrive(
    conn,
    organization_id: str,
    min_age_seconds: int,
    max_age_seconds: int,
    now: datetime | None = None,
) -> dict:
    """Read-only view of the failed notices that are genuinely redrivable
    right now: they belong to ``organization_id``, their age (time since the
    notice was first recorded) falls within
    ``[min_age_seconds, max_age_seconds]``, and their owning
    ``recovery_request`` has not reached a terminal status.

    "Terminal" is computed live against ``now`` using the same test
    :func:`recovery.retry_notification` applies (status already
    ``'completed'``, or status ``'expired'`` or ``now`` past
    ``expires_at``) -- but this function issues no writes. A request that is
    expired by the clock but whose ``status`` column has not yet been
    lazily flipped (because nothing has tried to complete or retry it since)
    is therefore excluded here without also being persisted as expired, so
    calling this function can never itself change what a later retry sees.

    Returns notification/request/account ids, per-notice ages, and a count
    -- never a token, retry locator, or recipient address.
    """
    validate_identifier("organization_id", organization_id)
    min_age_seconds, max_age_seconds = validate_age_range(min_age_seconds, max_age_seconds)

    now = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)

    rows = conn.execute(
        "SELECT n.notification_id, n.request_id, n.account_id, n.created_at, "
        "r.status AS request_status, r.expires_at AS request_expires_at "
        "FROM pending_notifications n "
        "JOIN recovery_requests r ON r.request_id = n.request_id "
        "WHERE n.organization_id = ? AND n.status = 'pending' "
        "ORDER BY n.created_at ASC, n.notification_id ASC",
        (organization_id,),
    ).fetchall()

    notifications = []
    for row in rows:
        is_terminal = row["request_status"] == "completed" or (
            row["request_status"] == "expired" or now > parse_iso(row["request_expires_at"])
        )
        if is_terminal:
            continue

        age_seconds = int((now - parse_iso(row["created_at"])).total_seconds())
        if age_seconds < min_age_seconds or age_seconds > max_age_seconds:
            continue

        notifications.append(
            {
                "notification_id": row["notification_id"],
                "request_id": row["request_id"],
                "account_id": row["account_id"],
                "age_seconds": age_seconds,
            }
        )

    return {
        "organization_id": organization_id,
        "min_age_seconds": min_age_seconds,
        "max_age_seconds": max_age_seconds,
        "eligible_count": len(notifications),
        "notifications": notifications,
    }


def describe_redrive_result(conn, organization_id: str, request_ids) -> dict:
    """Read-only, operator-facing view of what happened to a set of recovery
    requests: request ids, attempt ids, and outcomes -- never a token, retry
    locator, or recipient address.

    Every ``delivery_attempts`` row ever recorded for each request id is
    returned (not just the latest), ordered by ``attempted_at`` then
    ``attempt_id`` so repeated calls over unchanged data produce identical
    JSON -- the same stable-ordering guarantee :func:`preview_redrive` and
    :func:`consume_approval` already give.
    """
    validate_identifier("organization_id", organization_id)
    request_ids = validate_request_ids(request_ids)

    results = []
    for request_id in request_ids:
        request_row = conn.execute(
            "SELECT organization_id FROM recovery_requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        if request_row is None:
            raise NotFoundError(f"unknown request id: {request_id}")
        if request_row["organization_id"] != organization_id:
            raise ConflictError(
                f"request {request_id} belongs to organization {request_row['organization_id']}, not {organization_id}"
            )
        attempt_rows = conn.execute(
            "SELECT attempt_id, outcome FROM delivery_attempts "
            "WHERE request_id = ? ORDER BY attempted_at ASC, attempt_id ASC",
            (request_id,),
        ).fetchall()
        results.append(
            {
                "request_id": request_id,
                "attempts": [
                    {"attempt_id": row["attempt_id"], "outcome": row["outcome"]} for row in attempt_rows
                ],
            }
        )

    return {"organization_id": organization_id, "results": results}


def get_approval(conn, approval_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM redrive_approvals WHERE approval_id = ?", (approval_id,)
    ).fetchone()
    if row is None:
        return None
    request_ids = [
        r["request_id"]
        for r in conn.execute(
            "SELECT request_id FROM redrive_approval_requests WHERE approval_id = ? ORDER BY request_id ASC",
            (approval_id,),
        ).fetchall()
    ]
    return {
        "approval_id": row["approval_id"],
        "organization_id": row["organization_id"],
        "operator_id": row["operator_id"],
        "request_ids": request_ids,
        "expires_at": row["expires_at"],
        "created_at": row["created_at"],
    }


def create_approval(
    conn,
    approval_id: str,
    organization_id: str,
    operator_id: str,
    request_ids: list,
    expires_at: str,
    now: datetime | None = None,
) -> dict:
    """Durably record that ``operator_id`` approved redriving exactly
    ``request_ids`` for ``organization_id`` until ``expires_at``.

    This is an audit action only: unlike :func:`perform_redrive`, it never
    reads or writes ``pending_notifications`` and never touches the mail
    client, so recording an approval can never itself deliver anything.

    The request id set, organization, operator, and expiry are fixed the
    moment the approval is created and stored together in one durable
    record (unlike ``operator_decisions``/``batch_id``, which names a batch
    by a free-text label resolved against whatever batch file happens to be
    supplied later). Calling this again with the same ``approval_id`` and
    identical terms is a no-op that returns the existing durable record --
    safe after a client retry or a process restart. Calling it again with
    the same ``approval_id`` but any different organization, operator,
    expiry, or request id set is rejected, because an approval's terms must
    stay immutable once granted.
    """
    validate_identifier("approval_id", approval_id)
    validate_identifier("organization_id", organization_id)
    validate_identifier("operator_id", operator_id)
    request_ids = validate_request_ids(request_ids)
    parsed_expiry = parse_iso(expires_at)

    now = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)
    if parsed_expiry <= now:
        raise PolicyError(f"approval expiry {expires_at} is not in the future")

    operator = storage.get_operator(conn, operator_id)
    if operator is None:
        raise NotFoundError(f"unknown operator: {operator_id}")
    if operator["organization_id"] != organization_id:
        raise ConflictError(
            f"operator {operator_id} is scoped to organization {operator['organization_id']}, not {organization_id}"
        )

    for request_id in request_ids:
        request_row = conn.execute(
            "SELECT organization_id FROM recovery_requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        if request_row is None:
            raise NotFoundError(f"unknown request id: {request_id}")
        if request_row["organization_id"] != organization_id:
            raise ConflictError(
                f"request {request_id} belongs to organization {request_row['organization_id']}, not {organization_id}"
            )

    sorted_request_ids = sorted(request_ids)
    existing = get_approval(conn, approval_id)
    if existing is not None:
        if (
            existing["organization_id"] != organization_id
            or existing["operator_id"] != operator_id
            or existing["expires_at"] != expires_at
            or existing["request_ids"] != sorted_request_ids
        ):
            raise ConflictError(f"approval already recorded with different terms: {approval_id}")
        return existing

    created_at = now_iso()
    with conn:
        conn.execute(
            "INSERT INTO redrive_approvals(approval_id, organization_id, operator_id, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (approval_id, organization_id, operator_id, expires_at, created_at),
        )
        conn.executemany(
            "INSERT INTO redrive_approval_requests(approval_id, request_id) VALUES (?, ?)",
            [(approval_id, request_id) for request_id in sorted_request_ids],
        )

    return {
        "approval_id": approval_id,
        "organization_id": organization_id,
        "operator_id": operator_id,
        "request_ids": sorted_request_ids,
        "expires_at": expires_at,
        "created_at": created_at,
    }


def consume_approval(
    conn,
    mail_endpoint: str,
    approval_id: str,
    operator_id: str,
    organization_id: str,
    now: datetime | None = None,
) -> dict:
    """Consume a durable approval by retrying every one of its request ids
    that still has a pending notification.

    This wraps :func:`get_approval` -- it adds no storage of its own.
    ``operator_id`` and ``organization_id`` are checked against the
    operator's own registration and the approval's organization *before*
    anything is mutated, so a caller presenting the wrong organization is
    rejected with no side effects (the "role" check).

    "Consume once" is enforced without any "used" flag on the approval: each
    attempt goes through :func:`recovery.retry_notifications` (the same
    shared consumer the ordinary bearer-token retry route uses), which
    already refuses a notification whose status is no longer ``'pending'``.
    Once a request's notification has been delivered by an earlier
    consumption, a later call finds nothing pending left to retry for it, so
    replaying the same approval is naturally a no-op rather than a double
    delivery. The existing ``delivery_attempts`` rows written inside
    :func:`recovery.retry_notification` are the only audit trail this
    produces -- no separate audit record is written here.

    An approval whose ``expires_at`` has passed is rejected as a clean,
    side-effect-free no-op (``status: "stale"``, both lists empty) rather
    than an exception: presenting a stale approval is an expected, harmless
    occurrence (e.g. a delayed retry of this very call), not a caller error.

    The response is redacted the same way :func:`preview_redrive` is: never
    a token, retry locator, or recipient address, only ids and delivery
    status. Processing order is deterministic -- approval request ids
    ascending (as returned by :func:`get_approval`), then notification id
    ascending -- so repeated calls over unchanged data produce identical
    JSON. The batch actually retried in one call is capped at
    ``MAX_CONSUME_BATCH``; anything beyond the cap is reported as skipped.
    """
    validate_identifier("approval_id", approval_id)
    validate_identifier("operator_id", operator_id)
    validate_identifier("organization_id", organization_id)

    operator = storage.get_operator(conn, operator_id)
    if operator is None:
        raise NotFoundError(f"unknown operator: {operator_id}")
    if operator["organization_id"] != organization_id:
        raise ConflictError(
            f"operator {operator_id} is scoped to organization {operator['organization_id']}, not {organization_id}"
        )

    approval = get_approval(conn, approval_id)
    if approval is None:
        raise NotFoundError(f"unknown approval: {approval_id}")
    if approval["organization_id"] != organization_id:
        raise ConflictError(
            f"approval {approval_id} belongs to organization {approval['organization_id']}, not {organization_id}"
        )

    now = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)
    if now > parse_iso(approval["expires_at"]):
        return {
            "approval_id": approval_id,
            "organization_id": organization_id,
            "status": "stale",
            "processed": [],
            "skipped": [],
        }

    candidates = []
    for request_id in approval["request_ids"]:
        rows = conn.execute(
            "SELECT notification_id FROM pending_notifications "
            "WHERE request_id = ? AND status = 'pending' ORDER BY notification_id ASC",
            (request_id,),
        ).fetchall()
        candidates.extend(row["notification_id"] for row in rows)

    to_attempt, overflow = candidates[:MAX_CONSUME_BATCH], candidates[MAX_CONSUME_BATCH:]
    batch_result = recovery.retry_notifications(conn, mail_endpoint, to_attempt)
    processed = batch_result["processed"]
    skipped = batch_result["skipped"] + [
        {"notification_id": notification_id, "reason": "batch_limit_reached"} for notification_id in overflow
    ]

    return {
        "approval_id": approval_id,
        "organization_id": organization_id,
        "status": "consumed",
        "processed": processed,
        "skipped": skipped,
    }
