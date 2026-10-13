"""Business logic shared by the CLI and the loopback HTTP service.

Every function here takes a :class:`~oauthsvc.store.Store` explicitly so the
CLI and HTTP layers open the same on-disk database without sharing process
state, which is what lets an imported login recover cleanly across restarts.
"""
from __future__ import annotations

import sqlite3
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from . import errors, resume, security
from .store import Store

PENDING_AUTHORIZATION_TTL_SECONDS = 900


def create_account(store: Store, account_id: str, email: str, password: str) -> None:
    password_hash, salt, iterations = security.hash_password(password)
    try:
        store.create_account(account_id, email, password_hash, salt, iterations)
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"account {account_id!r} already exists") from exc


def register_client(store: Store, client_id: str, redirect_uri: str) -> None:
    try:
        store.register_client(client_id, redirect_uri)
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"client {client_id!r} is already registered") from exc


def import_legacy_login(
    store: Store, client_id: str, redirect_uri: str, legacy_handle: str, state: str
) -> dict:
    registered = store.get_callback(client_id)
    if registered is None:
        raise ValueError(f"client {client_id!r} is not registered")
    if registered != redirect_uri:
        raise ValueError("redirect_uri does not match the client's registered callback")

    login_id = security.new_token()
    locator = resume.encode_continuation_locator(legacy_handle, client_id)
    expires_at = time.time() + PENDING_AUTHORIZATION_TTL_SECONDS
    try:
        store.create_imported_pending_authorization(
            login_id, client_id, redirect_uri, state, legacy_handle, locator, expires_at
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError(
            f"legacy handle {legacy_handle!r} was already imported for client {client_id!r}"
        ) from exc

    resume_reference = {"kind": "imported", "client_id": client_id, "value": locator}
    return {"client_id": client_id, "login_id": login_id, "resume_reference": resume_reference}


def authorize(store: Store, client_id: str, redirect_uri: str, state: str) -> tuple[str, dict]:
    registered = store.get_callback(client_id)
    if registered is None or registered != redirect_uri:
        raise errors.UnregisteredCallback()

    login_id = security.new_token()
    expires_at = time.time() + PENDING_AUTHORIZATION_TTL_SECONDS
    store.create_native_pending_authorization(login_id, client_id, redirect_uri, state, expires_at)
    resume_reference = {"kind": "native", "client_id": client_id, "value": login_id}
    return login_id, resume_reference


def _append_query(url: str, **params: str) -> str:
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(params.items())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def complete_login(
    store: Store, login_id: str, account_id: str, password: str, code_ttl_seconds: int
) -> str:
    row = store.get_pending_authorization(login_id)
    if row is None:
        raise errors.InvalidLogin()
    if row["status"] != "pending" or time.time() > row["expires_at"]:
        raise errors.InvalidAuthorization()

    account = store.get_account(account_id)
    if account is None or not security.verify_password(
        password, account["password_hash"], account["password_salt"], account["password_iterations"]
    ):
        raise errors.InvalidCredentials()

    if row["kind"] == "imported":
        plan = store.get_migration_plan(login_id)
        if plan is None:
            raise errors.InvalidContinuation()
        resolved_client_id, resolved_callback = resume.recover_client_and_callback(
            plan["locator"], row["client_id"], store.get_callback
        )
        if resolved_callback is None or resolved_client_id != row["client_id"]:
            raise errors.InvalidContinuation()
    else:
        resolved_client_id, resolved_callback = row["client_id"], row["callback"]

    if not store.mark_pending_completed(login_id, account_id):
        raise errors.InvalidAuthorization()

    code = security.new_token()
    expires_at = time.time() + code_ttl_seconds
    store.create_authorization_code(code, resolved_client_id, account_id, login_id, expires_at)

    return _append_query(resolved_callback, code=code, state=row["state"])


def create_client_migration(store: Store, login_ids: list[str], destination_client_id: str) -> dict:
    """Move a batch of pending authorizations onto a destination client.

    Each pending row's ``client_id`` stays the authoritative owner; the
    destination is recorded only on the migration plan and its inventory
    rows, so source and destination client registrations never merge.
    """

    destination_callback = store.get_callback(destination_client_id)
    if destination_callback is None:
        raise errors.UnknownClient()

    now = time.time()
    entries = []
    pending_client_ids = []
    for login_id in login_ids:
        row = store.get_pending_authorization(login_id)
        if row is None:
            raise errors.UnknownLogin()
        if row["status"] != "pending" or now > row["expires_at"]:
            raise errors.InvalidAuthorization()
        if row["callback"] != destination_callback:
            raise errors.CallbackMismatch()
        if store.is_login_migrated(login_id):
            raise errors.DuplicatePlan()

        owning_client_id = row["client_id"]
        migration_handle = security.new_token()
        locator = resume.encode_continuation_locator(migration_handle, owning_client_id)
        entries.append(
            {
                "login_id": login_id,
                "account_id": row["account_id"],
                "owning_client_id": owning_client_id,
                "callback": row["callback"],
                "state": row["state"],
                "expires_at": row["expires_at"],
                "status": row["status"],
                "migration_handle": migration_handle,
                "locator": locator,
            }
        )
        pending_client_ids.append(owning_client_id)

    migration_id = security.new_token()
    try:
        store.create_client_migration(migration_id, destination_client_id, entries, now)
    except sqlite3.IntegrityError as exc:
        raise errors.DuplicatePlan() from exc

    return {"migration_id": migration_id, "pending_client_ids": pending_client_ids}


def dry_run_client_migration(store: Store, login_ids: list[str], destination_client_id: str) -> dict:
    """Report per-login callback compatibility for a prospective migration.

    Read-only: compares each pending authorization's exact callback against
    the destination client's registered callback and never calls
    ``store.create_client_migration`` or ``store.mark_pending_completed``, so
    no pending row's owning client is ever rewritten by a dry run.
    """

    destination_callback = store.get_callback(destination_client_id)
    if destination_callback is None:
        raise errors.UnknownClient()

    now = time.time()
    results = []
    for login_id in login_ids:
        row = store.get_pending_authorization(login_id)
        if row is None:
            results.append(
                {
                    "login_id": login_id,
                    "owning_client_id": None,
                    "callback": None,
                    "compatible": False,
                    "reason": "unknown_login",
                }
            )
            continue

        if row["status"] != "pending" or now > row["expires_at"]:
            results.append(
                {
                    "login_id": login_id,
                    "owning_client_id": row["client_id"],
                    "callback": row["callback"],
                    "compatible": False,
                    "reason": "not_pending",
                }
            )
            continue

        if row["callback"] != destination_callback:
            results.append(
                {
                    "login_id": login_id,
                    "owning_client_id": row["client_id"],
                    "callback": row["callback"],
                    "compatible": False,
                    "reason": "callback_mismatch",
                }
            )
            continue

        if store.is_login_migrated(login_id):
            results.append(
                {
                    "login_id": login_id,
                    "owning_client_id": row["client_id"],
                    "callback": row["callback"],
                    "compatible": False,
                    "reason": "conflicting_plan",
                }
            )
            continue

        results.append(
            {
                "login_id": login_id,
                "owning_client_id": row["client_id"],
                "callback": row["callback"],
                "compatible": True,
                "reason": None,
            }
        )

    return {
        "destination_client_id": destination_client_id,
        "compatible": all(entry["compatible"] for entry in results),
        "results": results,
    }


def commit_client_migration(store: Store, migration_id: str) -> dict:
    """Cut every member of a migration plan over to its destination client.

    Each member's cutover is its own atomic checkpoint
    (``Store.commit_migration_member``): a pending row's authoritative
    ``client_id`` is preserved until that one member's checkpoint completes,
    never before. Calling this again after a partial batch (some members
    committed, some not — for example after a restart mid-batch) finishes
    only the remaining members and never re-applies a completed checkpoint.
    Calling it again on an already fully committed plan is a no-op that
    returns the same ``"committed"`` status.
    """

    plan = store.get_client_migration_plan(migration_id)
    if plan is None:
        raise errors.UnknownMigration()
    if plan["status"] == "rolled_back":
        raise errors.MigrationRolledBack()

    if plan["status"] != "committed":
        for member in store.get_client_migration_members(migration_id):
            if member["cutover_status"] == "pending":
                store.commit_migration_member(
                    migration_id, member["login_id"], plan["destination_client_id"]
                )
        store.set_client_migration_plan_status(migration_id, "committed")

    return {
        "migration_id": migration_id,
        "destination_client_id": plan["destination_client_id"],
        "status": "committed",
    }


def rollback_client_migration(store: Store, migration_id: str) -> dict:
    """Revert a migration plan's cutovers and mark the plan rolled back.

    Every member whose checkpoint had already completed is reverted back to
    its original owning client, each as its own atomic step
    (``Store.rollback_migration_member``); a member never committed is only
    marked rolled back, with no ownership change. Rolling back an already
    rolled-back plan is a no-op that returns the same status. A rolled-back
    plan can never be committed again.
    """

    plan = store.get_client_migration_plan(migration_id)
    if plan is None:
        raise errors.UnknownMigration()

    if plan["status"] != "rolled_back":
        for member in store.get_client_migration_members(migration_id):
            if member["cutover_status"] != "rolled_back":
                store.rollback_migration_member(migration_id, member["login_id"])
        store.set_client_migration_plan_status(migration_id, "rolled_back")

    return {
        "migration_id": migration_id,
        "destination_client_id": plan["destination_client_id"],
        "status": "rolled_back",
    }


def get_migration_status(store: Store, migration_id: str, limit: int) -> dict:
    """Return a bounded view of one migration plan's status and members.

    ``member_count`` is the plan's true total; ``members`` lists at most
    ``limit`` of them, in stable creation order, so a very large migration
    plan can never make this response unbounded. Never includes a password,
    code, token, or opaque migration/continuation handle or locator.
    """

    plan = store.get_client_migration_plan(migration_id)
    if plan is None:
        raise errors.UnknownMigration()

    members = store.get_client_migration_members(migration_id, limit=limit)
    return {
        "migration_id": migration_id,
        "destination_client_id": plan["destination_client_id"],
        "status": plan["status"],
        "member_count": store.count_client_migration_members(migration_id),
        "members": [
            {
                "login_id": member["login_id"],
                "owning_client_id": member["owning_client_id"],
                "cutover_status": member["cutover_status"],
            }
            for member in members
        ],
    }


def resume_client_migration(
    store: Store,
    migration_id: str,
    account_id: str,
    password: str,
    code_ttl_seconds: int,
) -> str:
    """Resume the outstanding continuation in a committed migration."""

    plan = store.get_client_migration_plan(migration_id)
    if plan is None:
        raise errors.UnknownMigration()
    if plan["status"] == "rolled_back":
        raise errors.MigrationRolledBack()
    if plan["status"] != "committed":
        raise errors.MigrationNotCommitted()

    outstanding = [
        member
        for member in store.get_client_migration_members_with_continuation(
            migration_id
        )
        if member["continuation_status"] == "pending"
    ]
    if len(outstanding) == 1:
        login_id = outstanding[0]["login_id"]
        is_retry = False
    elif len(outstanding) == 0:
        already_resumed = [
            member
            for member in store.get_client_migration_members(migration_id)
            if member["account_id"] == account_id
        ]
        if len(already_resumed) != 1:
            raise errors.InvalidContinuation()
        login_id = already_resumed[0]["login_id"]
        is_retry = True
    else:
        raise errors.InvalidContinuation()

    row = store.get_pending_authorization(login_id)
    if row is None or time.time() > row["expires_at"]:
        raise errors.InvalidAuthorization()

    account = store.get_account(account_id)
    if account is None or not security.verify_password(
        password,
        account["password_hash"],
        account["password_salt"],
        account["password_iterations"],
    ):
        raise errors.InvalidCredentials()

    member = store.get_client_migration_member(login_id)
    source = store.get_migration_plan(login_id)
    saved = source["locator"] if source is not None else member["locator"]
    parts = saved.split(":", 2)
    client_id = parts[1] if len(parts) == 3 and parts[1] else row["client_id"]
    callback = store.get_callback(client_id)
    if callback is None or callback != row["callback"]:
        raise errors.InvalidContinuation()

    if not is_retry:
        if not store.mark_pending_completed(login_id, account_id):
            raise errors.InvalidAuthorization()
        store.set_client_migration_member_account(
            migration_id, login_id, account_id
        )

    code = security.new_token()
    expires_at = time.time() + code_ttl_seconds
    store.create_authorization_code(
        code, client_id, account_id, login_id, expires_at
    )

    return _append_query(callback, code=code, state=row["state"])


def _strip_callback_query(callback: str) -> str:
    parts = urlsplit(callback)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))


def inspect_client_migration(store: Store, migration_id: str, limit: int) -> dict:
    """Return a redacted, bounded inspection of one migration plan.

    Every lookup here is scoped to ``migration_id`` alone. ``member_count``
    and ``pending_continuation_count`` are true totals for this plan;
    ``members`` lists at most ``limit`` of them, in stable creation order, so
    a very large migration plan can never make this response unbounded.
    ``pending_continuation_count`` is the true total, across the whole plan,
    of members whose underlying login has not yet completed — independent
    of ``cutover_status``, which tracks the migration's own commit progress
    instead. Never includes a password, authorization code, access token,
    or opaque migration/continuation handle or locator, and each member's
    ``callback`` has its query component stripped.
    """

    plan = store.get_client_migration_plan(migration_id)
    if plan is None:
        raise errors.UnknownMigration()

    members = store.get_client_migration_members_with_continuation(migration_id, limit=limit)
    return {
        "migration_id": migration_id,
        "destination_client_id": plan["destination_client_id"],
        "status": plan["status"],
        "member_count": store.count_client_migration_members(migration_id),
        "pending_continuation_count": store.count_client_migration_pending_continuations(
            migration_id
        ),
        "members": [
            {
                "login_id": member["login_id"],
                "owning_client_id": member["owning_client_id"],
                "callback": _strip_callback_query(member["callback"]),
                "continuation_status": member["continuation_status"],
                "cutover_status": member["cutover_status"],
            }
            for member in members
        ],
    }


def get_client_migration_metrics(store: Store, migration_id: str) -> dict:
    """Return pure aggregate counts for one migration plan — never a member list.

    Unlike ``get_migration_status`` and ``inspect_client_migration``, this has
    no per-member list at all, so its response size never grows with the
    plan's membership: it is bounded by construction, not by a caller-chosen
    ``limit``. Every count is scoped to ``migration_id`` alone. The cutover
    counts (``cutover_pending_count``, ``cutover_committed_count``,
    ``cutover_rolled_back_count``) always sum to ``member_count``; the
    continuation counts (``continuation_pending_count``,
    ``continuation_completed_count``) reflect each member's *live* login
    status (the same live join ``inspect_client_migration`` uses) and also
    always sum to ``member_count``. Never includes a password, authorization
    code, access token, or opaque migration/continuation handle or locator.
    """

    plan = store.get_client_migration_plan(migration_id)
    if plan is None:
        raise errors.UnknownMigration()

    by_cutover = store.count_client_migration_members_by_cutover_status(migration_id)
    by_continuation = store.count_client_migration_members_by_continuation_status(migration_id)

    return {
        "migration_id": migration_id,
        "destination_client_id": plan["destination_client_id"],
        "status": plan["status"],
        "member_count": store.count_client_migration_members(migration_id),
        "cutover_pending_count": by_cutover.get("pending", 0),
        "cutover_committed_count": by_cutover.get("committed", 0),
        "cutover_rolled_back_count": by_cutover.get("rolled_back", 0),
        "continuation_pending_count": by_continuation.get("pending", 0),
        "continuation_completed_count": by_continuation.get("completed", 0),
    }


def exchange_token(store: Store, client_id: str, code: str, signing_key: str) -> dict:
    status, row = store.redeem_authorization_code(code, client_id, time.time())
    if status in ("not_found", "invalid"):
        raise errors.InvalidCode()
    if status == "wrong_client":
        raise errors.WrongClient()

    access_token = security.derive_access_token(signing_key, code)
    store.create_access_token(access_token, row["client_id"], row["account_id"], code)
    return {
        "access_token": access_token,
        "client_id": row["client_id"],
        "account_id": row["account_id"],
    }
