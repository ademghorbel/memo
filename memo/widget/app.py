"""Memo's desktop window: a frameless, always-on-top face.

Left-click: tidy the vault (safe fixes, backup first).  Drag: move.  Right-click: menu.
The checker runs on a worker thread; results come back through a queue so only
the main thread touches tkinter.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

from ..checker import Config, Report, check
from ..fixer import fix, undo
from . import face
from .text import details, summarize, tidied

KEY = "#ff00fe"  # painted where the window should be see-through (Windows)
FRAME_MS = 40
MIN_WORK_S = 1.2  # let the "working" face show even when the check is instant
DONE_S = 3.5
BUBBLE_BG = "#fffbe8"


def _dpi_aware() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


class MemoApp:
    def __init__(self, vault: Path, config: Config | None = None, every_min: float = 10):
        _dpi_aware()
        self.vault, self.config, self.every_ms = Path(vault), config or Config(), int(every_min * 60_000)
        self.root = root = tk.Tk()
        root.title("Memo")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        try:
            root.wm_attributes("-transparentcolor", KEY)
        except tk.TclError:  # not Windows: a plain square background
            pass
        self.k = max(1.0, root.winfo_fpixels("1i") / 96)
        size = int(face.SIZE * self.k)
        self.canvas = tk.Canvas(root, width=size, height=size, bg=KEY, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        x = root.winfo_screenwidth() - size - int(30 * self.k)
        y = root.winfo_screenheight() - size - int(70 * self.k)
        root.geometry(f"{size}x{size}+{x}+{y}")

        self.state = "working"
        self.report: Report | None = None
        self.results: queue.Queue = queue.Queue()
        self.pending = None
        self.busy = False
        self.silent = False
        self.started = 0.0
        self.revert_at = 0.0
        self.bubble: tk.Toplevel | None = None
        self.t0 = time.monotonic()

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Tidy up", command=lambda: self.run_check(tidy=True))
        self.menu.add_command(label="Check only", command=self.run_check)
        self.menu.add_command(label="What's wrong?", command=self.show_details)
        self.menu.add_command(label="Undo last tidy", command=self.run_undo)
        self.menu.add_command(label="Open vault folder", command=self.open_vault)
        self.menu.add_separator()
        self.menu.add_command(label="Quit", command=root.destroy)

        c = self.canvas
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._drag)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        root.bind("<Escape>", lambda e: root.destroy())

        self.run_check()
        if self.every_ms > 0:
            root.after(self.every_ms, self._auto_check)
        self._tick()

    # --- checking ---------------------------------------------------------
    def run_check(self, silent: bool = False, tidy: bool = False, undo_first: bool = False) -> None:
        if self.busy:
            return
        self.busy, self.silent, self.started = True, silent, time.monotonic()
        if not silent:
            self.state = "working"
            self.close_bubble()

        def work():
            try:
                note = None
                if undo_first:
                    note = "Undone:\n" + "\n".join(f"• {l}" for l in undo(self.vault)[:6])
                elif tidy:
                    note = tidied(fix(self.vault, self.config))
                self.results.put(("ok", (check(self.vault, self.config), note)))
            except Exception as e:  # shown on the face, never crashes the window
                self.results.put(("error", e))

        threading.Thread(target=work, daemon=True).start()

    def _auto_check(self) -> None:
        self.run_check(silent=True)
        self.root.after(self.every_ms, self._auto_check)

    def _finish(self, kind, value) -> None:
        self.busy = False
        if kind == "error":
            self.state = "error"
            self.say(f"Something broke:\n{value}")
            return
        value, note = value
        old = self.report.mood if self.report else None
        self.report = value
        if self.silent:
            self.state = value.mood
            if value.mood != old:
                self.say(summarize(value))
            return
        self.state, self.revert_at = "done", time.monotonic() + DONE_S
        self.say((note + "\n\n" if note else "") + summarize(value))

    # --- animation loop -----------------------------------------------------
    def _tick(self) -> None:
        now = time.monotonic()
        if self.pending is None:
            try:
                self.pending = self.results.get_nowait()
            except queue.Empty:
                pass
        if self.pending and (self.silent or now - self.started >= MIN_WORK_S):
            self._finish(*self.pending)
            self.pending = None
        if self.state == "done" and now >= self.revert_at and self.report:
            self.state = self.report.mood
        face.draw(self.canvas, self.state, now - self.t0, self.k)
        self.root.after(FRAME_MS, self._tick)

    # --- mouse --------------------------------------------------------------
    def _press(self, e) -> None:
        self._grab = (e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y())
        self._moved = False

    def _drag(self, e) -> None:
        x0, y0, wx, wy = self._grab
        dx, dy = e.x_root - x0, e.y_root - y0
        if abs(dx) + abs(dy) > 4:
            self._moved = True
            self.close_bubble()
        if self._moved:
            self.root.geometry(f"+{wx + dx}+{wy + dy}")

    def _release(self, e) -> None:
        if not self._moved:
            self.run_check(tidy=True)

    # --- bubble -------------------------------------------------------------
    def say(self, text: str) -> None:
        self.close_bubble()
        k = self.k
        b = self.bubble = tk.Toplevel(self.root)
        b.overrideredirect(True)
        b.attributes("-topmost", True)
        frame = tk.Frame(b, bg=BUBBLE_BG, highlightbackground=face.INK, highlightthickness=max(1, int(2 * k)))
        frame.pack()
        label = tk.Label(frame, text=text, bg=BUBBLE_BG, fg=face.INK, justify="left",
                         font=("Segoe UI", 10), wraplength=int(260 * k), padx=int(10 * k), pady=int(8 * k))
        label.pack()
        for wdg in (b, frame, label):
            wdg.bind("<Button-1>", lambda e: self.close_bubble())
        b.update_idletasks()
        bw, bh = b.winfo_width(), b.winfo_height()
        rx, ry, size = self.root.winfo_x(), self.root.winfo_y(), self.root.winfo_width()
        x = rx - bw - int(4 * k)
        if x < 0:
            x = rx + size + int(4 * k)
        y = max(0, ry + int(20 * k))
        b.geometry(f"+{x}+{y}")
        b.after(4000 + 60 * len(text), lambda bb=b: self.close_bubble(bb))

    def close_bubble(self, only: tk.Toplevel | None = None) -> None:
        if self.bubble is not None and (only is None or only is self.bubble):
            try:
                self.bubble.destroy()
            except tk.TclError:
                pass
            self.bubble = None

    def run_undo(self) -> None:
        self.run_check(undo_first=True)

    def show_details(self) -> None:
        if self.report:
            self.say(details(self.report))

    def open_vault(self) -> None:
        if hasattr(os, "startfile"):
            os.startfile(self.vault)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(self.vault)])

    def run(self) -> None:
        self.root.mainloop()
