from __future__ import annotations

import multiprocessing
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from price_tool.audit import append_event, read_audit
from price_tool.errors import PriceToolError
from price_tool.workflow import commit_stage, create_stage
from tests.support import write_catalog, write_changes

FIXED_TIME = "2026-01-15T12:00:00Z"
FORK_AVAILABLE = "fork" in multiprocessing.get_all_start_methods()


def fixed_clock() -> str:
    return FIXED_TIME


def _append_worker(
    audit_name: str,
    worker_number: int,
    barrier: Any,
    result_queue: Any,
) -> None:
    """Contend at the empty-chain read to make an unlocked fork reproducible."""

    import price_tool.audit as audit_module

    original_read = audit_module._read_audit_unlocked

    def delayed_empty_read(path: Path) -> list[dict[str, Any]]:
        events = original_read(path)
        if not events:
            time.sleep(0.05)
        return events

    try:
        barrier.wait(timeout=5)
        with patch.object(audit_module, "_read_audit_unlocked", delayed_empty_read):
            event = append_event(
                Path(audit_name),
                event_type="stage_created",
                occurred_at=FIXED_TIME,
                stage_id=f"{worker_number:064x}",
                venue_id="demo-venue-alpha",
                evidence={"worker_number": worker_number},
            )
        result_queue.put(("success", event["sequence"]))
    except Exception as exc:  # The parent asserts the exact worker outcome.
        result_queue.put(("error", type(exc).__name__, str(exc)))


def _commit_worker(
    catalog_name: str,
    stage_name: str,
    audit_name: str,
    stage_id: str,
    barrier: Any,
    active: Any,
    peak_active: Any,
    counter_lock: Any,
    result_queue: Any,
) -> None:
    """Observe how many commit transaction bodies can run concurrently."""

    import price_tool.workflow as workflow_module

    original_commit = workflow_module._commit_stage_locked

    def observed_commit(*args: Any, **kwargs: Any) -> dict[str, Any]:
        with counter_lock:
            active.value += 1
            peak_active.value = max(peak_active.value, active.value)
        try:
            time.sleep(0.10)
            return original_commit(*args, **kwargs)
        finally:
            with counter_lock:
                active.value -= 1

    try:
        barrier.wait(timeout=5)
        with patch.object(workflow_module, "_commit_stage_locked", observed_commit):
            result = commit_stage(
                Path(catalog_name),
                Path(stage_name),
                Path(audit_name),
                stage_id,
                clock=fixed_clock,
            )
        result_queue.put(("success", result["verified"]))
    except PriceToolError as exc:
        result_queue.put(("error", exc.code))
    except Exception as exc:  # The parent asserts the exact worker outcome.
        result_queue.put(("unexpected", type(exc).__name__, str(exc)))


@unittest.skipUnless(FORK_AVAILABLE, "requires POSIX fork and advisory file locks")
class ConcurrencyTests(unittest.TestCase):
    @staticmethod
    def _join(processes: list[Any]) -> None:
        for process in processes:
            process.join(timeout=10)
        stuck = [process for process in processes if process.is_alive()]
        for process in stuck:
            process.terminate()
            process.join(timeout=2)
        if stuck:
            raise AssertionError("worker process did not finish")

    def test_concurrent_audit_writers_preserve_one_hash_chain(self) -> None:
        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "audit.jsonl"
            worker_count = 8
            barrier = context.Barrier(worker_count)
            result_queue = context.Queue()
            processes = [
                context.Process(
                    target=_append_worker,
                    args=(str(audit_path), number, barrier, result_queue),
                )
                for number in range(1, worker_count + 1)
            ]
            for process in processes:
                process.start()
            self._join(processes)
            results = [result_queue.get(timeout=2) for _ in processes]
            result_queue.close()
            result_queue.join_thread()

            self.assertEqual(worker_count, sum(result[0] == "success" for result in results))
            self.assertTrue(all(process.exitcode == 0 for process in processes))
            events = read_audit(audit_path)
            self.assertEqual(
                list(range(1, worker_count + 1)),
                [event["sequence"] for event in events],
            )
            self.assertEqual(worker_count, len({event["stage_id"] for event in events}))

    def test_concurrent_commits_serialize_the_catalog_transaction(self) -> None:
        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "catalog.json"
            changes_path = root / "changes.csv"
            stage_path = root / "stage.json"
            audit_path = root / "audit.jsonl"
            write_catalog(catalog_path)
            write_changes(changes_path)
            stage = create_stage(
                catalog_path,
                changes_path,
                stage_path,
                audit_path,
                clock=fixed_clock,
            )

            barrier = context.Barrier(2)
            active = context.Value("i", 0)
            peak_active = context.Value("i", 0)
            counter_lock = context.Lock()
            result_queue = context.Queue()
            common_args = (
                str(catalog_path),
                str(stage_path),
                str(audit_path),
                stage["stage_id"],
                barrier,
                active,
                peak_active,
                counter_lock,
                result_queue,
            )
            processes = [
                context.Process(target=_commit_worker, args=common_args)
                for _ in range(2)
            ]
            for process in processes:
                process.start()
            self._join(processes)
            results = [result_queue.get(timeout=2) for _ in processes]
            result_queue.close()
            result_queue.join_thread()

            self.assertEqual(1, peak_active.value)
            self.assertCountEqual([("success", True), ("error", "state_conflict")], results)
            self.assertTrue(all(process.exitcode == 0 for process in processes))
            self.assertEqual(
                ["stage_created", "commit_started", "commit_verified"],
                [event["event_type"] for event in read_audit(audit_path)],
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
