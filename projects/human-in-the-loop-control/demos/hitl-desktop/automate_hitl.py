"""
HITL automator against mock console (same process pattern).

Demo modes:
  python automate_hitl.py           # launches console + runs happy path
  python automate_hitl.py --fail    # demonstrates verify fail -> HITL pause
  python automate_hitl.py --log-path /tmp/hitl-run.log
  python smoke_test.py              # scripted checks (requires Tk and a display)

This is a LAB demonstration of write-then-verify + human gate patterns.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

# Local import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mock_console import MockConsole  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def write_run_log(lines: list[str], log_path: Path | None) -> Path | None:
    """Write only to an explicit path outside the tracked project tree."""
    if log_path is None:
        return None
    target = log_path.expanduser().resolve()
    if target == PROJECT_ROOT or PROJECT_ROOT in target.parents:
        raise ValueError("log path must be outside the project tree")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def run_automation(
    console: MockConsole,
    force_fail: bool,
    *,
    interactive: bool = True,
    log_path: Path | None = None,
) -> list[str]:
    log: list[str] = []
    target_id = "4000104"
    new_price = "2.55"
    log.append(f"PLAN: set {target_id} price -> {new_price}")

    if force_fail:
        console.set_price(target_id, "999.99")
        log.append("SETUP: injected anomaly to force verify fail")
    else:
        console.set_price(target_id, new_price)
        log.append(f"WRITE: {target_id} = {new_price}")

    time.sleep(0.05)
    read_back = console.read_price(target_id)
    log.append(f"VERIFY read_back={read_back}")

    if read_back != new_price:
        log.append("HITL: verification failed - human must intervene")
        console.status.set("HITL PAUSE: verify failed - refine automation / correct data")
        msg = (
            f"Expected price {new_price}, read {read_back}.\n"
            "Pattern: intervene, root-cause, refine automation, then retry."
        )
        if interactive:
            # Prefer direct call so demos still work if after() is delayed;
            # schedule on UI thread when called from a worker.
            def _warn() -> None:
                messagebox.showwarning("HITL PAUSE (lab)", msg)

            try:
                if threading.current_thread() is threading.main_thread():
                    _warn()
                else:
                    console.after(0, _warn)
            except Exception as e:  # noqa: BLE001 - lab demo must not crash
                log.append(f"HITL warn UI skipped: {e}")
        else:
            log.append("HITL: non-interactive mode (no dialog)")
    else:
        log.append("OK: verify passed - safe to continue batch (lab)")
        console.status.set("Verify OK (lab)")

    written = write_run_log(log, log_path)
    log.append("LOG: explicit external path written" if written else "LOG: not written")
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fail", action="store_true", help="Force verification failure for HITL demo")
    ap.add_argument(
        "--log-path",
        type=Path,
        help="Optional output path outside this project tree; no log is written by default",
    )
    args = ap.parse_args()

    app = MockConsole()

    def _start() -> None:
        time.sleep(0.4)
        try:
            lines = run_automation(
                app,
                force_fail=args.fail,
                interactive=True,
                log_path=args.log_path,
            )
            print("\n".join(lines))
        except Exception as e:
            print("FAIL", e)

    threading.Thread(target=_start, daemon=True).start()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
