"""
launcher.py — Launches Chrome with the CDP debug port enabled.

Chrome only allows one process per user profile. If Chrome is already open,
launching it again with --remote-debugging-port just hands off to the existing
process (which has no debug port), causing ECONNREFUSED.

This launcher solves that by using a dedicated profile directory, so the
debug-enabled Chrome runs as a completely separate process alongside any
existing Chrome windows.

Usage:
    python launcher.py
"""

import subprocess
import sys
import os

# Common Chrome installation paths on Windows
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

CDP_PORT = 9222

# Dedicated profile directory so this Chrome runs independently of any
# existing Chrome session. Stored inside the project folder.
_PROFILE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "chrome_profile",
)


def find_chrome() -> str:
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    return None


def main():
    chrome = find_chrome()
    if not chrome:
        print("[launcher] Could not find Chrome automatically.")
        chrome = input("Enter full path to chrome.exe: ").strip().strip('"')
        if not os.path.exists(chrome):
            print(f"[launcher] File not found: {chrome}")
            sys.exit(1)

    os.makedirs(_PROFILE_DIR, exist_ok=True)

    print(f"[launcher] Launching Chrome from: {chrome}")
    print(f"[launcher] CDP debug port: {CDP_PORT}")
    print(f"[launcher] Profile directory: {_PROFILE_DIR}")
    print()
    print("[launcher] A new Chrome window will open — log into Total Battle there.")
    print("[launcher] Keep this terminal open. When ready, run: python main.py")
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
