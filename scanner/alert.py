"""
alert.py — Alerts the user when a Mercenary Exchange is found.
Shows a Tkinter overlay window and plays a system beep.
"""

import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional

from scanner.detector import Detection


def _play_beep():
    """Play a system alert sound (cross-platform best-effort)."""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        return
    except ImportError:
        pass
    try:
        import subprocess
        subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                       capture_output=True, timeout=2)
        return
    except Exception:
        pass
    # Last resort: terminal bell
    print("\a", end="", flush=True)


class AlertOverlay:
    """
    A borderless Tkinter window that floats on top of all windows,
    showing the detection result. Closes automatically after a timeout
    or when the user clicks it.
    """

    def __init__(self, detection: Detection, auto_close_seconds: int = 30):
        self._detection = detection
        self._auto_close = auto_close_seconds
        self._root: Optional[tk.Tk] = None

    def show(self):
        """Display the overlay (runs in a background thread so it doesn't block scanning)."""
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self):
        root = tk.Tk()
        self._root = root
        root.title("Mercenary Exchange Found!")
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.92)
        root.overrideredirect(True)  # no title bar

        # Centre on screen
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w, h = 420, 180
        x = (sw - w) // 2
        y = 40  # near top so it doesn't cover the game
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.configure(bg="#1a1a2e")

        big_font = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        small_font = tkfont.Font(family="Segoe UI", size=11)

        tk.Label(
            root, text="⚔  MERCENARY EXCHANGE FOUND  ⚔",
            bg="#1a1a2e", fg="#f5c518",
            font=big_font, pady=12,
        ).pack(fill="x")

        cx, cy = self._detection.center
        tk.Label(
            root,
            text=f"Location on screen: ({cx}, {cy})   Confidence: {self._detection.confidence:.0%}",
            bg="#1a1a2e", fg="#cccccc",
            font=small_font,
        ).pack()

        tk.Label(
            root,
            text="Click anywhere to dismiss",
            bg="#1a1a2e", fg="#888888",
            font=small_font, pady=8,
        ).pack()

        btn = tk.Button(
            root, text="Dismiss", command=root.destroy,
            bg="#f5c518", fg="#1a1a2e",
            font=small_font, relief="flat", padx=16, pady=4,
        )
        btn.pack()

        root.bind("<Button-1>", lambda e: root.destroy())
        root.after(self._auto_close * 1000, root.destroy)
        root.mainloop()


def trigger_alert(detection: Detection):
    """
    Sound the alarm and show the overlay for a found Mercenary Exchange.
    Safe to call from any thread.
    """
    from config.settings import ALERT_SOUND, ALERT_OVERLAY

    print(f"[alert] FOUND Mercenary Exchange at screen position {detection.center} "
          f"(confidence {detection.confidence:.0%})")

    if ALERT_SOUND:
        _play_beep()

    if ALERT_OVERLAY:
        overlay = AlertOverlay(detection)
        overlay.show()
