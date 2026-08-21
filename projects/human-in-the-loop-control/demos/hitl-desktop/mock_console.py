"""
Synthetic control console: dense grid + status, lab only.
Run: python mock_console.py
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox


class MockConsole(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Synthetic Control Console (LAB) - Menu Item Maintenance")
        self.geometry("900x420")
        self.minsize(800, 360)

        frm = ttk.Frame(self, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Property: LAB-001  |  Record type: Menu Item Master  |  Mode: LAB").pack(anchor=tk.W)
        ttk.Label(
            frm,
            text="INDEPENDENT PORTFOLIO DEMO · SYNTHETIC DATA · NO AFFILIATION · NO PRODUCTION ACTION",
        ).pack(anchor=tk.W)

        cols = ("id", "name", "price", "zone", "status")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
        headings = {
            "id": "Object #",
            "name": "Definition Name",
            "price": "Price",
            "zone": "Zone/Location",
            "status": "Status",
        }
        widths = {"id": 100, "name": 220, "price": 80, "zone": 180, "status": 100}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=6)

        # Seed rows (synthetic)
        self._rows = [
            ("4000093", "Strawberry Cobbler", "3.03", "Property: LAB", "Active"),
            ("4000104", "Peanut Butter Cookie", "2.42", "Property: LAB", "Active"),
            ("4000105", "Lemon Blueberry Muffin", "3.37", "Property: LAB", "Active"),
            ("4000119", "Turtle Cupcake", "4.21", "Property: LAB", "Active"),
            ("4000127", "Boston Cream Cupcake", "4.21", "Property: LAB", "Active"),
        ]
        for r in self._rows:
            self.tree.insert("", tk.END, iid=r[0], values=r)

        bar = ttk.Frame(frm)
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="Save (human)", command=self._save).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Inject bad price (demo fail)", command=self._inject_bad).pack(side=tk.LEFT, padx=4)
        self.status = tk.StringVar(value="Ready (lab data only)")
        ttk.Label(bar, textvariable=self.status).pack(side=tk.LEFT, padx=12)

        # Same-process hook used by the lab automator.
        self.bind("<<AutomatorSetPrice>>", self._on_set_price)

    def _save(self) -> None:
        self.status.set("Saved (lab): human confirm path")
        messagebox.showinfo("LAB", "Human save acknowledged (lab only).")

    def _inject_bad(self) -> None:
        # Corrupt a cell so verify fails
        iid = "4000104"
        vals = list(self.tree.item(iid, "values"))
        vals[2] = "999.99"
        self.tree.item(iid, values=vals)
        self.status.set("Injected anomaly price on 4000104")

    def set_price(self, object_id: str, price: str) -> None:
        if object_id not in self.tree.get_children():
            raise KeyError(object_id)
        vals = list(self.tree.item(object_id, "values"))
        vals[2] = price
        self.tree.item(object_id, values=vals)
        self.status.set(f"UI write object={object_id} price={price}")
        self.update_idletasks()

    def read_price(self, object_id: str) -> str:
        vals = self.tree.item(object_id, "values")
        return str(vals[2])

    def _on_set_price(self, event: tk.Event) -> None:  # noqa: ARG002
        pass


def main() -> None:
    app = MockConsole()
    # Expose on root for same-process automator
    app.console = app  # type: ignore[attr-defined]
    app.mainloop()


if __name__ == "__main__":
    main()
