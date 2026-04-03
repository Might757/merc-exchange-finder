"""
control_panel.py — Tkinter control panel for the Mercenary Exchange Finder.

Launch with:
    python main.py --gui
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ControlPanel:
    BG = "#0f0f1a"
    PANEL = "#1a1a2e"
    ACCENT = "#f5c518"
    TEXT = "#e0e0e0"
    DIM = "#888888"
    GREEN = "#4caf50"
    RED = "#f44336"
    BTN_BG = "#2a2a3e"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Mercenary Exchange Finder")
        self.root.configure(bg=self.BG)

        self._scan_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._status_restore_job = None

        self._build_ui()
        self._refresh_log_table()

    # ------------------------------------------------------------------ UI build

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # Title
        title_frame = tk.Frame(self.root, bg=self.PANEL, pady=12)
        title_frame.pack(fill="x")
        big = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        tk.Label(title_frame, text="⚔  Mercenary Exchange Finder",
                 bg=self.PANEL, fg=self.ACCENT, font=big).pack()

        # Settings
        settings_frame = tk.LabelFrame(self.root, text=" Settings ",
                                       bg=self.BG, fg=self.DIM,
                                       font=("Segoe UI", 9))
        settings_frame.pack(fill="x", **pad)

        self._cols_var = tk.IntVar(value=20)
        self._rows_var = tk.IntVar(value=15)
        self._start_col_var = tk.IntVar(value=0)
        self._start_row_var = tk.IntVar(value=0)
        self._threshold_var = tk.DoubleVar(value=0.75)
        self._speed_var = tk.StringVar(value="Normal")
        self._ocr_var = tk.BooleanVar(value=True)
        self._test_mode_var = tk.BooleanVar(value=False)

        def _lbl(parent, text, row, col=0, span=1, anchor="w", fg=None):
            tk.Label(parent, text=text, bg=self.BG, fg=fg or self.TEXT,
                     font=("Segoe UI", 9), anchor=anchor).grid(
                row=row, column=col, columnspan=span, sticky="w", padx=8, pady=3)

        def _spin(parent, var, lo, hi, row, step=1, fmt=None, width=6):
            kw = dict(from_=lo, to=hi, textvariable=var, width=width,
                      bg=self.BTN_BG, fg=self.TEXT,
                      buttonbackground=self.BTN_BG, relief="flat",
                      increment=step)
            if fmt:
                kw["format"] = fmt
            w = tk.Spinbox(parent, **kw)
            w.grid(row=row, column=1, sticky="w", padx=8, pady=3)
            return w

        # ── Grid size ──────────────────────────────────────────────────
        _lbl(settings_frame, "Grid columns:", 0)
        _spin(settings_frame, self._cols_var, 1, 200, 0)

        _lbl(settings_frame, "Grid rows:", 1)
        _spin(settings_frame, self._rows_var, 1, 200, 1)

        # ── Start offset ───────────────────────────────────────────────
        # Separator label
        tk.Frame(settings_frame, bg=self.DIM, height=1).grid(
            row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 2))
        _lbl(settings_frame, "Start position  (navigate the map to your start area first)",
             3, span=3, fg=self.DIM)

        _lbl(settings_frame, "Start from col:", 4)
        _spin(settings_frame, self._start_col_var, 0, 199, 4)

        _lbl(settings_frame, "Start from row:", 5)
        _spin(settings_frame, self._start_row_var, 0, 199, 5)

        # ── Detection ─────────────────────────────────────────────────
        tk.Frame(settings_frame, bg=self.DIM, height=1).grid(
            row=6, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 2))

        _lbl(settings_frame, "Match threshold (0–1):", 7)
        _spin(settings_frame, self._threshold_var, 0.40, 0.99, 7, step=0.01, fmt="%.2f")

        _lbl(settings_frame, "Scan speed:", 8)
        speed_menu = tk.OptionMenu(settings_frame, self._speed_var,
                                   "Slow", "Normal", "Fast", "Fastest")
        speed_menu.config(bg=self.BTN_BG, fg=self.TEXT, relief="flat",
                          activebackground=self.ACCENT, activeforeground=self.BG,
                          highlightthickness=0, font=("Segoe UI", 9))
        speed_menu["menu"].config(bg=self.BTN_BG, fg=self.TEXT)
        speed_menu.grid(row=8, column=1, sticky="w", padx=8, pady=3)

        # Speed note
        _lbl(settings_frame,
             "Fastest may miss icons if map tiles load slowly — try Fast first",
             9, span=3, fg=self.DIM)

        _lbl(settings_frame, "OCR confirmation:", 10)
        tk.Checkbutton(settings_frame, variable=self._ocr_var,
                       bg=self.BG, fg=self.TEXT, selectcolor=self.BTN_BG,
                       activebackground=self.BG).grid(
            row=10, column=1, sticky="w", padx=8, pady=3)

        _lbl(settings_frame, "Test mode (skip OCR keywords):", 11)
        test_frame = tk.Frame(settings_frame, bg=self.BG)
        test_frame.grid(row=11, column=1, sticky="w", padx=8, pady=3)
        tk.Checkbutton(test_frame, variable=self._test_mode_var,
                       bg=self.BG, fg=self.TEXT, selectcolor=self.BTN_BG,
                       activebackground=self.BG).pack(side="left")
        tk.Label(test_frame, text="(accepts any icon match)",
                 bg=self.BG, fg=self.DIM, font=("Segoe UI", 8)).pack(side="left", padx=4)

        # ── Progress ──────────────────────────────────────────────────
        prog_frame = tk.LabelFrame(self.root, text=" Progress ",
                                   bg=self.BG, fg=self.DIM, font=("Segoe UI", 9))
        prog_frame.pack(fill="x", **pad)

        self._progress_bar = ttk.Progressbar(prog_frame, mode="determinate")
        self._progress_bar.pack(fill="x", padx=8, pady=(6, 2))

        self._progress_label = tk.Label(prog_frame, text="0 / 0 cells scanned",
                                        bg=self.BG, fg=self.TEXT, font=("Segoe UI", 9))
        self._progress_label.pack(pady=(0, 2))

        self._threshold_label = tk.Label(prog_frame, text="Threshold: —",
                                         bg=self.BG, fg=self.DIM, font=("Segoe UI", 8))
        self._threshold_label.pack(pady=(0, 6))

        # ── Status ────────────────────────────────────────────────────
        self._status_label = tk.Label(self.root, text="Status: Idle",
                                      bg=self.BG, fg=self.DIM, font=("Segoe UI", 9))
        self._status_label.pack(**pad)

        # ── Buttons ───────────────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=self.BG)
        btn_frame.pack(pady=4)
        btn_cfg = dict(bg=self.BTN_BG, fg=self.TEXT, relief="flat",
                       font=("Segoe UI", 10, "bold"), padx=14, pady=6,
                       cursor="hand2", activebackground=self.ACCENT,
                       activeforeground=self.BG)

        self._start_btn = tk.Button(btn_frame, text="▶  Start Scan",
                                    command=self._start_scan, **btn_cfg)
        self._start_btn.grid(row=0, column=0, padx=6)

        self._stop_btn = tk.Button(btn_frame, text="■  Stop",
                                   command=self._stop_scan,
                                   state="disabled", **btn_cfg)
        self._stop_btn.grid(row=0, column=1, padx=6)

        self._reset_btn = tk.Button(btn_frame, text="↺  Reset State",
                                    command=self._reset_state, **btn_cfg)
        self._reset_btn.grid(row=0, column=2, padx=6)

        tk.Label(self.root, text="Hotkey: F9 = Stop scan",
                 bg=self.BG, fg=self.DIM, font=("Segoe UI", 8)).pack(pady=(0, 4))

        # ── Finds table ───────────────────────────────────────────────
        finds_frame = tk.LabelFrame(
            self.root,
            text=" Found Exchanges  (click row to copy coordinates) ",
            bg=self.BG, fg=self.DIM, font=("Segoe UI", 9))
        finds_frame.pack(fill="both", expand=True, **pad)

        cols_def = ("Time", "Grid", "K : X : Y", "Conf", "OCR")
        self._tree = ttk.Treeview(finds_frame, columns=cols_def,
                                   show="headings", height=8)
        col_widths = {"Time": 140, "Grid": 70, "K : X : Y": 180, "Conf": 60, "OCR": 50}
        for col in cols_def:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=col_widths[col], anchor="center", minwidth=40)

        scrollbar = ttk.Scrollbar(finds_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=6)
        scrollbar.pack(side="right", fill="y", pady=6, padx=(0, 8))

        self._tree.bind("<ButtonRelease-1>", self._on_row_click)

        self._copy_label = tk.Label(self.root, text="",
                                    bg=self.BG, fg=self.ACCENT,
                                    font=("Segoe UI", 9, "bold"))
        self._copy_label.pack(pady=(0, 6))

        # Styles
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=self.PANEL, fieldbackground=self.PANEL,
                         foreground=self.TEXT, rowheight=24)
        style.configure("Treeview.Heading", background=self.BTN_BG,
                         foreground=self.ACCENT, font=("Segoe UI", 8, "bold"))
        style.map("Treeview", background=[("selected", "#2a3a5e")])
        style.configure("TProgressbar", troughcolor=self.BTN_BG, background=self.ACCENT)

    # ------------------------------------------------------------------ Row click

    def _on_row_click(self, event):
        selected = self._tree.selection()
        if not selected:
            return
        values = self._tree.item(selected[0], "values")
        if not values:
            return
        coord_str = values[2]
        if coord_str and coord_str != "—":
            self.root.clipboard_clear()
            self.root.clipboard_append(coord_str)
            self._show_copy_feedback(coord_str)

    def _show_copy_feedback(self, coord_str: str):
        if self._status_restore_job:
            self.root.after_cancel(self._status_restore_job)
        self._copy_label.config(text=f"Copied: {coord_str}")
        self._status_restore_job = self.root.after(
            2500, lambda: self._copy_label.config(text=""))

    # ------------------------------------------------------------------ Actions

    def _start_scan(self):
        if self._scan_thread and self._scan_thread.is_alive():
            return
        self._stop_event.clear()
        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._set_status("Connecting...", self.DIM)
        self._scan_thread = threading.Thread(target=self._scan_worker, daemon=True)
        self._scan_thread.start()

    def _stop_scan(self):
        self._stop_event.set()
        self._set_status("Stopping after current cell...", self.DIM)
        self._stop_btn.config(state="disabled")

    def _reset_state(self):
        if self._scan_thread and self._scan_thread.is_alive():
            messagebox.showwarning("Scan running", "Stop the scan before resetting.")
            return
        if messagebox.askyesno("Reset state", "Clear all saved scan progress?"):
            from scanner.grid_tracker import GridTracker
            t = GridTracker(cols=self._cols_var.get(), rows=self._rows_var.get())
            t.reset()
            self._update_progress(0, self._cols_var.get() * self._rows_var.get())
            self._set_status("State reset. Ready.", self.DIM)

    # ------------------------------------------------------------------ Worker

    def _scan_worker(self):
        import keyboard
        import pyautogui
        import scanner.capture as capture
        import scanner.navigator as nav
        from scanner.navigator import pan_right, pan_down, pan_left, hover_at
        from scanner.detector import detect, get_adaptive_threshold, read_game_coords
        from scanner.alert import trigger_alert
        from scanner.grid_tracker import GridTracker
        from scanner.logger import log_find
        import config.settings as S

        cols = self._cols_var.get()
        rows = self._rows_var.get()
        start_col = self._start_col_var.get()
        start_row = self._start_row_var.get()

        S.MATCH_THRESHOLD = self._threshold_var.get()
        S.USE_OCR_CONFIRMATION = False if self._test_mode_var.get() else self._ocr_var.get()

        # Apply speed preset
        preset_name = self._speed_var.get()
        land_max_w, drag_dur, move_dur, pause_val = S.SPEED_PRESETS.get(
            preset_name, S.SPEED_PRESETS["Normal"])
        nav.DRAG_DURATION = drag_dur
        nav.MOVE_DURATION = move_dur
        pyautogui.PAUSE = pause_val

        import scanner.detector as det_mod
        det_mod._adaptive_threshold = self._threshold_var.get()

        keyboard.add_hotkey('f9', self._stop_scan)

        self.root.after(0, lambda: self._set_status("Connecting to Chrome...", self.DIM))

        try:
            page = capture.connect(S.CDP_URL)
        except ConnectionError as e:
            self.root.after(0, lambda: self._set_status(f"Connection failed: {e}", self.RED))
            self.root.after(0, lambda: self._start_btn.config(state="normal"))
            try:
                keyboard.remove_hotkey('f9')
            except Exception:
                pass
            return

        tracker = GridTracker(cols=cols, rows=rows)

        # Pre-mark cells before the start offset so the scanner jumps straight there
        if start_row > 0 or start_col > 0:
            print(f"[worker] Skipping to start position row={start_row}, col={start_col}")
            for r in range(rows):
                for c in range(cols):
                    if r < start_row or (r == start_row and c < start_col):
                        if not tracker.is_scanned(r, c):
                            tracker.mark_scanned(r, c)

        found_this_session = 0

        try:
            for row in range(rows):
                for col in range(cols):
                    if self._stop_event.is_set():
                        break

                    scanned, total = tracker.progress()
                    self.root.after(0, lambda s=scanned, t=total: self._update_progress(s, t))
                    self.root.after(0, lambda thr=get_adaptive_threshold():
                        self._threshold_label.config(
                            text=f"Threshold: {thr:.2f}  (adaptive)  |  Speed: {preset_name}"))

                    if tracker.is_scanned(row, col):
                        if col < cols - 1:
                            pan_right(page, S.PAN_STEP_X)
                        continue

                    self.root.after(0, lambda r=row, c=col, s=scanned, t=total:
                        self._set_status(
                            f"Scanning ({r},{c})  [{s}/{t}]  — F9 to stop", self.GREEN))

                    frame = capture.wait_for_stable_frame(drag_duration=drag_dur, land_max_wait=land_max_w)
                    detections, raw_count = detect(frame)

                    if raw_count > 0 and not detections:
                        self.root.after(0, lambda: self._set_status(
                            "Match found but rejected by OCR — try Test Mode or lower threshold",
                            self.ACCENT))
                        time.sleep(1.0)

                    if detections:
                        for det in detections:
                            found_this_session += 1
                            trigger_alert(det)
                            # Hover over the icon so game shows its real K/X/Y
                            cx, cy = det.center
                            hover_at(cx, cy, settle_time=0.4)
                            fresh_frame = capture.screenshot_numpy()
                            coords = read_game_coords(fresh_frame)
                            log_find(det, frame, grid_row=row, grid_col=col, coords=coords)
                        self.root.after(0, self._refresh_log_table)

                    tracker.mark_scanned(row, col)

                    if col < cols - 1:
                        pan_right(page, S.PAN_STEP_X)

                if self._stop_event.is_set():
                    break

                if row < rows - 1:
                    pan_down(page, S.PAN_STEP_Y)
                    for _ in range(cols - 1):
                        pan_left(page, S.PAN_STEP_X)
                        time.sleep(0.02)

        finally:
            try:
                keyboard.remove_hotkey('f9')
            except Exception:
                pass
            capture.disconnect()

        scanned, total = tracker.progress()
        if tracker.is_complete():
            self.root.after(0, lambda: self._set_status(
                f"Scan complete! Found {found_this_session} exchange(s) this session.", self.ACCENT))
        else:
            self.root.after(0, lambda: self._set_status(
                f"Paused at {scanned}/{total} cells. Click Start to resume.", self.DIM))

        self.root.after(0, lambda: self._start_btn.config(state="normal"))
        self.root.after(0, lambda: self._stop_btn.config(state="disabled"))
        self.root.after(0, lambda: self._update_progress(scanned, total))

    # ------------------------------------------------------------------ Helpers

    def _set_status(self, msg: str, colour: str):
        self._status_label.config(text=f"Status: {msg}", fg=colour)

    def _update_progress(self, scanned: int, total: int):
        self._progress_bar["maximum"] = max(total, 1)
        self._progress_bar["value"] = scanned
        self._progress_label.config(text=f"{scanned} / {total} cells scanned")

    def _refresh_log_table(self):
        from scanner.logger import get_all_finds
        finds = get_all_finds()
        for item in self._tree.get_children():
            self._tree.delete(item)
        for f in reversed(finds[-100:]):
            k = f.get("k_coord", "")
            x = f.get("x_coord", "")
            y = f.get("y_coord", "")
            coord_str = f"K{k} X{x} Y{y}" if (k and x and y) else "—"
            self._tree.insert("", "end", values=(
                f.get("timestamp", ""),
                f"({f.get('grid_row','?')},{f.get('grid_col','?')})",
                coord_str,
                f"{float(f.get('confidence', 0)):.0%}",
                "Yes" if f.get("ocr_confirmed") == "True" else "No",
            ))


def launch_gui():
    root = tk.Tk()
    root.geometry("780x900")
    root.minsize(600, 750)
    root.resizable(True, True)
    ControlPanel(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
