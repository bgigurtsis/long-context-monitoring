"""Tests for restart-safe phase transitions: crash, duplicate, conflict, separate process."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from auditlog.httpd import ROUTE_ACTIONS
from auditlog.planner import OptimisticConflictError, Plan, load_plan, save_plan
from auditlog.rollout import (
    CohortTransitionRecord,
    IdempotencyKeyReuseError,
    UnknownTransitionKindError,
    advance_phase,
    rollback_phase,
    transition_phase,
)
from auditlog.service import AuditLogService
from auditlog.storage import JsonFileEventStore

REPO_ROOT = Path(__file__).resolve().parent.parent


class RolloutTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        self.plan_path = self.tmp_dir / "plan.json"
        self.rollout_path = self.tmp_dir / "rollout.json"
        self.log_path = self.tmp_dir / "log.json"

    def log_store(self) -> JsonFileEventStore:
        return JsonFileEventStore(self.log_path)

    def events(self):
        return AuditLogService(self.log_store()).events()


class BasicTransitionTests(RolloutTestCase):
    def test_advance_moves_the_plan_and_records_one_audit_event(self) -> None:
        outcome = advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="advance-1",
            to_phase="canary",
            expected_revision=0,
            actor="operator:mina",
        )
        self.assertEqual(outcome.from_phase, "preparation")
        self.assertEqual(outcome.to_phase, "canary")
        self.assertEqual(outcome.plan_revision, 1)
        self.assertFalse(outcome.replayed)

        plan = load_plan(self.plan_path)
        self.assertEqual(plan.phase, "canary")
        self.assertEqual(plan.revision, 1)

        events = self.events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action, "phase.advance")
        self.assertEqual(events[0].outcome, "preparation->canary")
        self.assertEqual(events[0].sequence, 1)

    def test_rollback_moves_the_plan_back(self) -> None:
        advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="advance-1",
            to_phase="canary",
            expected_revision=0,
            actor="operator:mina",
        )
        outcome = rollback_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="rollback-1",
            to_phase="preparation",
            expected_revision=1,
            actor="operator:mina",
        )
        self.assertEqual(outcome.from_phase, "canary")
        self.assertEqual(outcome.to_phase, "preparation")
        self.assertEqual(outcome.plan_revision, 2)

        plan = load_plan(self.plan_path)
        self.assertEqual(plan.phase, "preparation")
        self.assertEqual(plan.revision, 2)

        events = self.events()
        self.assertEqual([event.action for event in events], ["phase.advance", "phase.rollback"])
        self.assertEqual([event.sequence for event in events], [1, 2])

    def test_cohort_transitions_are_recorded_but_dispatch_never_changes(self) -> None:
        save_plan(self.plan_path, Plan(phase="preparation").with_target("canary-a", "v2"), expected_revision=0)

        outcome = advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="advance-1",
            to_phase="canary",
            expected_revision=1,
            actor="operator:mina",
        )

        self.assertEqual(
            outcome.cohort_transitions,
            (CohortTransitionRecord(cohort="canary-a", from_assignment="v1", to_assignment="v1"),),
        )
        # Both phases are pinned to v1, so no cohort's assignment ever
        # actually moves. This phase transition itself never touches the
        # bare V1-only ROUTE_ACTIONS constant either way -- the live
        # server's separately-installed, protected V2 aliases (see
        # auditlog.httpd.build_server) are unaffected by it.
        self.assertNotIn(("POST", "/v2/entries"), ROUTE_ACTIONS)
        self.assertNotIn(("GET", "/v2/entries"), ROUTE_ACTIONS)

    def test_unknown_kind_is_rejected(self) -> None:
        with self.assertRaises(UnknownTransitionKindError):
            transition_phase(
                plan_path=self.plan_path,
                rollout_path=self.rollout_path,
                log_store=self.log_store(),
                idempotency_key="bad-kind",
                kind="teleport",
                to_phase="canary",
                expected_revision=0,
                actor="operator:mina",
            )


class DuplicateIdempotencyKeyTests(RolloutTestCase):
    def test_repeated_key_replays_the_cached_outcome_without_reapplying(self) -> None:
        first = advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="dup-key",
            to_phase="canary",
            expected_revision=0,
            actor="operator:mina",
        )
        second = advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="dup-key",
            to_phase="canary",
            expected_revision=0,
            actor="operator:mina",
        )

        self.assertFalse(first.replayed)
        self.assertTrue(second.replayed)
        self.assertEqual(first.audit_event_id, second.audit_event_id)
        self.assertEqual(first.plan_revision, second.plan_revision)

        self.assertEqual(load_plan(self.plan_path).revision, 1)
        self.assertEqual(len(self.events()), 1)

    def test_repeated_key_with_different_arguments_is_rejected(self) -> None:
        advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="dup-key",
            to_phase="canary",
            expected_revision=0,
            actor="operator:mina",
        )
        with self.assertRaises(IdempotencyKeyReuseError):
            advance_phase(
                plan_path=self.plan_path,
                rollout_path=self.rollout_path,
                log_store=self.log_store(),
                idempotency_key="dup-key",
                to_phase="preparation",
                expected_revision=0,
                actor="operator:mina",
            )


class ConflictTests(RolloutTestCase):
    def test_stale_expected_revision_from_a_different_key_is_rejected(self) -> None:
        advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="key-a",
            to_phase="canary",
            expected_revision=0,
            actor="operator:mina",
        )
        with self.assertRaises(OptimisticConflictError):
            advance_phase(
                plan_path=self.plan_path,
                rollout_path=self.rollout_path,
                log_store=self.log_store(),
                idempotency_key="key-b",
                to_phase="canary",
                expected_revision=0,
                actor="operator:priya",
            )

        # The rejected attempt left the plan and the audit trail untouched.
        self.assertEqual(load_plan(self.plan_path).revision, 1)
        self.assertEqual(len(self.events()), 1)

    def test_conflict_against_a_writer_outside_the_rollout_module_is_rejected(self) -> None:
        base = save_plan(self.plan_path, Plan(phase="preparation"), expected_revision=0)
        # A writer that never goes through auditlog.rollout at all.
        save_plan(self.plan_path, base.with_target("control-a", "v1"), expected_revision=base.revision)

        with self.assertRaises(OptimisticConflictError):
            advance_phase(
                plan_path=self.plan_path,
                rollout_path=self.rollout_path,
                log_store=self.log_store(),
                idempotency_key="key-c",
                to_phase="canary",
                expected_revision=base.revision,
                actor="operator:mina",
            )


class CrashRecoveryTests(RolloutTestCase):
    def test_crash_before_the_plan_is_saved_is_retried_cleanly(self) -> None:
        from auditlog import rollout as rollout_module

        real_save_plan = rollout_module.save_plan
        calls = {"n": 0}

        def flaky_save_plan(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("simulated crash before the plan is saved")
            return real_save_plan(*args, **kwargs)

        with mock.patch.object(rollout_module, "save_plan", side_effect=flaky_save_plan):
            with self.assertRaises(RuntimeError):
                advance_phase(
                    plan_path=self.plan_path,
                    rollout_path=self.rollout_path,
                    log_store=self.log_store(),
                    idempotency_key="crash-key",
                    to_phase="canary",
                    expected_revision=0,
                    actor="operator:mina",
                )

        self.assertFalse(self.plan_path.exists())
        self.assertEqual(self.events(), [])

        outcome = advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="crash-key",
            to_phase="canary",
            expected_revision=0,
            actor="operator:mina",
        )
        self.assertFalse(outcome.replayed)
        self.assertEqual(outcome.plan_revision, 1)
        self.assertEqual(load_plan(self.plan_path).phase, "canary")
        self.assertEqual(len(self.events()), 1)

    def test_crash_after_the_plan_is_saved_before_the_audit_event_resumes_without_reapplying(self) -> None:
        with mock.patch.object(AuditLogService, "record", side_effect=RuntimeError("simulated crash after save")):
            with self.assertRaises(RuntimeError):
                advance_phase(
                    plan_path=self.plan_path,
                    rollout_path=self.rollout_path,
                    log_store=self.log_store(),
                    idempotency_key="crash-key",
                    to_phase="canary",
                    expected_revision=0,
                    actor="operator:mina",
                )

        # The plan already moved; the crash happened strictly after that.
        self.assertEqual(load_plan(self.plan_path).phase, "canary")
        self.assertEqual(load_plan(self.plan_path).revision, 1)
        self.assertEqual(self.events(), [])

        outcome = advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="crash-key",
            to_phase="canary",
            expected_revision=0,
            actor="operator:mina",
        )
        self.assertFalse(outcome.replayed)
        self.assertEqual(outcome.plan_revision, 1)  # not bumped a second time
        self.assertEqual(load_plan(self.plan_path).revision, 1)
        events = self.events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].sequence, 1)

        # A further call now hits the pure cache-hit path.
        replayed = advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="crash-key",
            to_phase="canary",
            expected_revision=0,
            actor="operator:mina",
        )
        self.assertTrue(replayed.replayed)
        self.assertEqual(replayed.audit_event_id, outcome.audit_event_id)
        self.assertEqual(len(self.events()), 1)

    def test_crash_after_the_audit_event_before_marking_complete_does_not_duplicate_the_event(self) -> None:
        from auditlog import rollout as rollout_module

        real_write_operations = rollout_module._write_operations
        calls = {"n": 0}

        def flaky_write_operations(path, operations):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("simulated crash before marking the operation complete")
            return real_write_operations(path, operations)

        with mock.patch.object(rollout_module, "_write_operations", side_effect=flaky_write_operations):
            with self.assertRaises(RuntimeError):
                advance_phase(
                    plan_path=self.plan_path,
                    rollout_path=self.rollout_path,
                    log_store=self.log_store(),
                    idempotency_key="crash-key",
                    to_phase="canary",
                    expected_revision=0,
                    actor="operator:mina",
                )

        # Both the plan save and the audit append already happened.
        self.assertEqual(load_plan(self.plan_path).phase, "canary")
        self.assertEqual(len(self.events()), 1)
        operations = json.loads(self.rollout_path.read_text(encoding="utf-8"))
        self.assertEqual(operations["crash-key"]["status"], "pending")

        outcome = advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="crash-key",
            to_phase="canary",
            expected_revision=0,
            actor="operator:mina",
        )
        self.assertFalse(outcome.replayed)
        self.assertEqual(len(self.events()), 1)  # still exactly one event, not two
        operations = json.loads(self.rollout_path.read_text(encoding="utf-8"))
        self.assertEqual(operations["crash-key"]["status"], "completed")


class SeparateProcessTests(RolloutTestCase):
    def _run_in_subprocess(
        self,
        *,
        key: str,
        kind: str,
        to_phase: str,
        expected_revision: int,
        actor: str = "operator:subprocess",
    ) -> dict:
        script = f"""
import json
from pathlib import Path

from auditlog.rollout import transition_phase
from auditlog.storage import JsonFileEventStore

try:
    outcome = transition_phase(
        plan_path=Path({str(self.plan_path)!r}),
        rollout_path=Path({str(self.rollout_path)!r}),
        log_store=JsonFileEventStore(Path({str(self.log_path)!r})),
        idempotency_key={key!r},
        kind={kind!r},
        to_phase={to_phase!r},
        expected_revision={expected_revision!r},
        actor={actor!r},
    )
    print(json.dumps({{
        "ok": True,
        "kind": outcome.kind,
        "from_phase": outcome.from_phase,
        "to_phase": outcome.to_phase,
        "plan_revision": outcome.plan_revision,
        "audit_event_id": outcome.audit_event_id,
        "replayed": outcome.replayed,
    }}))
except Exception as exc:  # noqa: BLE001 - reporting the failure back to the parent process
    print(json.dumps({{"ok": False, "error": type(exc).__name__}}))
"""
        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            check=True,
            timeout=30,
        )
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_advance_in_a_separate_process_is_visible_to_the_parent_process(self) -> None:
        result = self._run_in_subprocess(key="sub-1", kind="advance", to_phase="canary", expected_revision=0)
        self.assertTrue(result["ok"])
        self.assertFalse(result["replayed"])

        plan = load_plan(self.plan_path)
        self.assertEqual(plan.phase, "canary")
        self.assertEqual(plan.revision, 1)
        self.assertEqual(len(self.events()), 1)

    def test_conflict_from_a_separate_process_is_detected_by_the_parent_process(self) -> None:
        result = self._run_in_subprocess(key="sub-1", kind="advance", to_phase="canary", expected_revision=0)
        self.assertTrue(result["ok"])

        with self.assertRaises(OptimisticConflictError):
            advance_phase(
                plan_path=self.plan_path,
                rollout_path=self.rollout_path,
                log_store=self.log_store(),
                idempotency_key="parent-key",
                to_phase="canary",
                expected_revision=0,  # stale: the subprocess already moved the plan to revision 1
                actor="operator:mina",
            )

    def test_duplicate_key_from_a_separate_process_replays_in_the_parent_process(self) -> None:
        subprocess_result = self._run_in_subprocess(
            key="shared-key", kind="advance", to_phase="canary", expected_revision=0
        )
        self.assertTrue(subprocess_result["ok"])
        self.assertFalse(subprocess_result["replayed"])

        outcome = advance_phase(
            plan_path=self.plan_path,
            rollout_path=self.rollout_path,
            log_store=self.log_store(),
            idempotency_key="shared-key",
            to_phase="canary",
            expected_revision=0,
            actor="operator:subprocess",
        )
        self.assertTrue(outcome.replayed)
        self.assertEqual(outcome.audit_event_id, subprocess_result["audit_event_id"])
        self.assertEqual(outcome.plan_revision, subprocess_result["plan_revision"])
        self.assertEqual(len(self.events()), 1)


if __name__ == "__main__":
    unittest.main()
