"""
launcher.py — Launches Chrome with the CDP debug port enabled.

Chrome only allows one process per user profile. If Chrome is already open,
launching it again with --remote-debugging-port just hands off to the existing
process (which has no debug port), causing ECONNREFUSED.

This launcher uses a dedicated profile directory to force a fully separate
Chrome process alongside any existing Chrome windows.

Usage:
    python launcher.py
"""

import subprocess
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox

CDP_PORT = 9222

_PROFILE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "chrome_profile",
)


def _find_chrome_registry() -> str | None:
    """Check the Windows Registry for Chrome's install path — most reliable method."""
    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for subkey in (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
            ):
                try:
                    key = winreg.OpenKey(root, subkey)
                    path, _ = winreg.QueryValueEx(key, None)
                    winreg.CloseKey(key)
                    if path and os.path.exists(path):
                        return path
                except (FileNotFoundError, OSError):
                    continue
    except ImportError:
        pass
    return None


def _find_chrome_common_paths() -> str | None:
    """Check common Chrome installation paths as a fallback."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        # Non-C: drives
        r"D:\Program Files\Google\Chrome\Application\chrome.exe",
        r"D:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _ask_user_for_chrome() -> str | None:
    """Show a file picker dialog so the user can locate chrome.exe themselves."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "Chrome Not Found",
        "Could not find Chrome automatically.\n\n"
        "Click OK and then browse to your chrome.exe file.\n"
        "It is usually inside:\n"
        "  C:\\Program Files\\Google\\Chrome\\Application\\"
    )
    path = filedialog.askopenfilename(
        title="Select chrome.exe",
        filetypes=[("Chrome executable", "chrome.exe"), ("All executables", "*.exe")],
        initialdir=r"C:\Program Files",
    )
    root.destroy()
    return path if path and os.path.exists(path) else None


def find_chrome() -> str | None:
    # Registry is the most reliable source on Windows
    path = _find_chrome_registry()
    if path:
        return path
    # Fall back to common path list
    path = _find_chrome_common_paths()
    if path:
        return path
    return None


def main():
    chrome = find_chrome()

    if not chrome:
        print("[launcher] Chrome not found via registry or common paths.")
        chrome = _ask_user_for_chrome()

    if not chrome:
        print("[launcher] No Chrome executable selected. Exiting.")
        sys.exit(1)

    os.makedirs(_PROFILE_DIR, exist_ok=True)

    print(f"[launcher] Chrome found: {chrome}")
    print(f"[launcher] CDP debug port: {CDP_PORT}")
    print(f"[launcher] Profile directory: {_PROFILE_DIR}")
    print()
    print("[launcher] A new Chrome window will open — log into Total Battle there.")
    print("[launcher] Keep this terminal open. When ready, run: python main.py --gui")
    print("[launcher] Close this terminal to close the scanner Chrome.\n")

    subprocess.run([
        chrome,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={_PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
    ])


if __name__ == "__main__":
    main()
