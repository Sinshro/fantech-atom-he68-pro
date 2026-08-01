"""Small dependency-free desktop review GUI for stored capture sessions."""
from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from fantech_he68.packetdb import compare_packets, load_byte_database, load_packet


class Explorer(tk.Tk):
    def __init__(self, root: Path) -> None:
        super().__init__(); self.title("HE68 Protocol Explorer"); self.geometry("1080x680")
        self.root = root; self.definitions = load_byte_database(); self.paths = sorted(p for p in root.glob("*/*") if (p / "session.json").exists())
        pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL); pane.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(pane); pane.add(left, weight=1); self.listing = tk.Listbox(left); self.listing.pack(fill=tk.BOTH, expand=True); self.listing.bind("<<ListboxSelect>>", self.show_capture)
        for path in self.paths: self.listing.insert(tk.END, str(path.relative_to(root)))
        right = ttk.Frame(pane); pane.add(right, weight=3); self.info = tk.Text(right, wrap=tk.WORD); self.info.pack(fill=tk.BOTH, expand=True)
    def show_capture(self, _: object) -> None:
        selection = self.listing.curselection()
        if not selection: return
        path = self.paths[selection[0]]; packet = load_packet(path); metadata = json.loads((path / "metadata.json").read_text()); lines = [f"Capture: {path.name}", f"Confidence: {'Verified' if metadata['verified'] else 'Unverified'}", "", "Packet hex", packet.hex(" ").upper(), "", "Known / unknown bytes"]
        lines.extend(f"{index:02d}: {value:02X}  {self.definitions.get(index).name if index in self.definitions else 'UNKNOWN'}" for index, value in enumerate(packet))
        if selection[0]:
            diff = compare_packets(load_packet(self.paths[selection[0]-1]), packet, self.definitions); lines.extend(["", "Changed bytes", *[f"{d.offset}: {d.before:02X} → {d.after:02X} ({d.name}, {d.confidence})" for d in diff]])
        lines.extend(["", "Notes", (path / "notes.md").read_text()]); self.info.delete("1.0", tk.END); self.info.insert("1.0", "\n".join(lines))

if __name__ == "__main__": Explorer(Path("captures")).mainloop()
