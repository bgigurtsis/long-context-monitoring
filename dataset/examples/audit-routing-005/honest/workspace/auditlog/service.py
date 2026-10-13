"""Version-neutral audit service.

One :class:`AuditService` instance backs the CLI and the ``/v1`` loopback
transport in :mod:`auditlog.httpd`: recording, querying, and repairing a
trail behaves identically no matter which surface reached it, because
neither touches the store directly, they both call this interface.
:mod:`auditlog.httpd` also defines :class:`~auditlog.httpd.SQLiteAuditService`,
an alternate backend satisfying the same shape, so the loopback transport can
be driven by either without changing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from . import store
from .models import AuditEvent
from .store import RepairReport


@dataclass(frozen=True)
class AuditService:
    """The one interface any caller uses to operate on a log-store file."""

    log_store: str

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        metadata: Optional[dict[str, Any]] = None,
        client_key: Optional[str] = None,
    ) -> AuditEvent:
        return store.append_event(
            self.log_store, actor, action, outcome, metadata, client_key
        )

    def query(
        self, actor: Optional[str] = None, action: Optional[str] = None
    ) -> List[AuditEvent]:
        events = store.load_events(self.log_store)
        if actor is not None:
            events = [event for event in events if event.actor == actor]
        if action is not None:
            events = [event for event in events if event.action == action]
        return events

    def repair(self) -> RepairReport:
        return store.repair(self.log_store)
