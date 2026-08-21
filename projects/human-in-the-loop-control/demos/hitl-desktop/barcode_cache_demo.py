"""Clean-room identifier-cache and human-save-gate demonstration.

The module operates only on bundled, invented records and in-memory state.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from hitl_core import (
    DEMO_CACHE,
    HELD_MANUAL_MENU_ITEM_ID,
    approve_lab_save,
    fresh_rows,
    reread_staged_updates,
    resolve_from_cache,
    stage_price_updates,
    validate_held_row,
)


class BarcodeCacheDemo(tk.Tk):
    """Screen-shareable GUI around the pure synthetic workflow above."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Synthetic Identifier Cache Demo")
        self.geometry("1140x620")
        self.minsize(980, 540)
        self.rows = fresh_rows()
        self.cache = dict(DEMO_CACHE)
        self.force_mismatch = tk.BooleanVar(value=False)
        self.status_text = tk.StringVar(value="Ready. Synthetic lab data only.")
        self._build()
        self._refresh()

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            outer,
            text="INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION",
            foreground="#9a3412",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, pady=(0, 6))
        ttk.Label(
            outer,
            text="Barcode cache → held unknowns → staged updates → reread → human save",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="Independent clean-room demo with bundled, invented records and in-memory state.",
        ).pack(anchor=tk.W, pady=(2, 10))

        columns = (
            "barcode",
            "item",
            "current",
            "requested",
            "menu_id",
            "staged",
            "reread",
            "status",
        )
        self.table = ttk.Treeview(outer, columns=columns, show="headings", height=12)
        headings = {
            "barcode": "Barcode",
            "item": "Item",
            "current": "Current",
            "requested": "Requested",
            "menu_id": "Menu Item ID",
            "staged": "Staged",
            "reread": "Reread",
            "status": "Status",
        }
        widths = {
            "barcode": 120,
            "item": 175,
            "current": 75,
            "requested": 75,
            "menu_id": 95,
            "staged": 75,
            "reread": 75,
            "status": 210,
        }
        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], anchor=tk.W)
        self.table.pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(outer)
        controls.pack(fill=tk.X, pady=(10, 4))
        ttk.Button(controls, text="1. Resolve from cache", command=self._resolve).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(
            controls, text="2. Validate held row (lab)", command=self._validate_held
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(controls, text="3. Stage proposed prices", command=self._stage).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(controls, text="4. Reread and verify", command=self._verify).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(controls, text="5. Approve save (human)", command=self._approve).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(controls, text="Reset", command=self._reset).pack(side=tk.RIGHT)

        options = ttk.Frame(outer)
        options.pack(fill=tk.X, pady=(2, 6))
        ttk.Checkbutton(
            options,
            text="Inject one reread mismatch to demonstrate fail-closed behavior",
            variable=self.force_mismatch,
        ).pack(side=tk.LEFT)
        ttk.Label(options, textvariable=self.status_text).pack(side=tk.RIGHT)

        self.log = tk.Text(outer, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=False)
        self._log("This lab changes in-memory synthetic state only.")

    def _refresh(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        for row in self.rows:
            self.table.insert(
                "",
                tk.END,
                values=(
                    row.barcode,
                    row.item_name,
                    f"${row.current_price}",
                    f"${row.requested_price}",
                    row.menu_item_id or "-",
                    f"${row.staged_price}" if row.staged_price else "-",
                    f"${row.reread_price}" if row.reread_price else "-",
                    row.status,
                ),
            )

    def _log(self, line: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, line + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _resolve(self) -> None:
        hits, held = resolve_from_cache(self.rows, self.cache)
        self._refresh()
        self.status_text.set(f"{hits} cache hits; {held} held for manual lookup")
        self._log(
            f"CACHE: {hits} known barcode(s) received menu-item IDs immediately; "
            f"{held} unknown(s) were held instead of guessed."
        )

    def _validate_held(self) -> None:
        held = next((row for row in self.rows if not row.menu_item_id), None)
        if held is None:
            messagebox.showinfo("Lab", "No held rows remain.")
            return
        validate_held_row(self.rows, self.cache, held.barcode, HELD_MANUAL_MENU_ITEM_ID)
        self._refresh()
        self.status_text.set("Held barcode manually validated in the lab")
        self._log(
            f"HUMAN: confirmed synthetic barcode {held.barcode} as menu item "
            f"{HELD_MANUAL_MENU_ITEM_ID}; the validated mapping is now reusable."
        )

    def _stage(self) -> None:
        try:
            stage_price_updates(self.rows)
        except ValueError as exc:
            messagebox.showwarning("Staging blocked", str(exc))
            self._log(f"HOLD: {exc}")
            return
        self._refresh()
        self.status_text.set("Proposed updates staged; nothing saved")
        self._log("STAGE: entered proposed prices without finalizing the synthetic state.")

    def _verify(self) -> None:
        mismatch = self.rows[1].barcode if self.force_mismatch.get() else ""
        try:
            passed = reread_staged_updates(self.rows, mismatch_barcode=mismatch)
        except ValueError as exc:
            messagebox.showwarning("Verification blocked", str(exc))
            self._log(f"HOLD: {exc}")
            return
        self._refresh()
        if passed:
            self.status_text.set("Reread passed; awaiting human save approval")
            self._log("VERIFY: every staged value matched the request. Save still requires a person.")
        else:
            self.status_text.set("Reread mismatch; save blocked")
            self._log("HOLD: reread mismatch detected. The batch cannot be approved.")

    def _approve(self) -> None:
        try:
            approve_lab_save(self.rows)
        except ValueError as exc:
            messagebox.showwarning("Save blocked", str(exc))
            self._log(f"BLOCKED: {exc}")
            return
        self._refresh()
        self.status_text.set("Saved only after explicit human approval (lab)")
        self._log("HUMAN SAVE: approved and persisted the verified synthetic values.")

    def _reset(self) -> None:
        self.rows = fresh_rows()
        self.cache = dict(DEMO_CACHE)
        self.force_mismatch.set(False)
        self.status_text.set("Ready. Synthetic lab data only.")
        self._refresh()
        self._log("RESET: restored the synthetic request and cache.")


def main() -> int:
    BarcodeCacheDemo().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
