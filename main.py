"""
main.py — Mercenary Exchange Finder entry point.

Usage:
    python main.py          # start/resume scan
    python main.py --reset  # clear saved scan state and start fresh
    python main.py --gui    # launch control panel UI instead of CLI

Before running:
    1. Launch Chrome with: python launcher.py  (or chrome.exe --remote-debugging-port=9222)
    2. Open Total Battle and navigate to the world map
    3. Run this script
"""

import sys
import time
import signal
import argparse

import scanner.capture as capture
from scanner.navigator import pan_right, pan_down, pan_left, hover_at
from scanner.detector import detect, draw_detections, get_adaptive_threshold, read_game_coords
from scanner.alert import trigger_alert
from scanner.grid_tracker import GridTracker
from scanner.logger import log_find, get_log_path
from config.settings import (
    CDP_URL,
    PAN_STEP_X, PAN_STEP_Y,
    SCAN_COLS, SCAN_ROWS,
    SPEED_PRESETS,
)

_stop_flag = False


def _handle_sigint(sig, frame):
    global _stop_flag
    print("\n[main] Stop requested — finishing current cell then saving state...")
    _stop_flag = True


def scan_grid(page, tracker: GridTracker, speed: str = "Normal"):
    """
    Scan the world map in a raster pattern, skipping already-scanned cells.
    Saves state after each cell so a resume picks up where it left off.
    """
    global _stop_flag
    found_count = 0
    min_w, max_w, _, _, _ = SPEED_PRESETS.get(speed, SPEED_PRESETS["Normal"])

    cols = SCAN_COLS or 20
    rows = SCAN_ROWS or 15

    for row in range(rows):
        for col in range(cols):
            if _stop_flag:
                return found_count

            # Skip cells already scanned in a previous session
            if tracker.is_scanned(row, col):
                scanned, total = tracker.progress()
                print(f"[main] Skipping cell ({row},{col}) — already scanned  [{scanned}/{total}]")
                # Still need to pan to keep position correct
                if col < cols - 1:
                    pan_right(page, PAN_STEP_X)
                continue

            scanned, total = tracker.progress()
            print(f"[main] Scanning ({row},{col})  [{scanned}/{total}]  "
                  f"threshold={get_adaptive_threshold():.2f}")

            frame = capture.wait_for_stable_frame(min_wait=min_w, max_wait=max_w)
            detections, raw_count = detect(frame)

            if raw_count > 0 and not detections:
                print("[main] Match found but rejected by OCR. Try lowering threshold or disabling OCR.")

            if detections:
                for det in detections:
                    found_count += 1
                    print(f"[main] *** MERCENARY EXCHANGE DETECTED *** {det}")
                    trigger_alert(det)
                    # Hover over the icon so the game shows its K/X/Y coordinates
                    cx, cy = det.center
                    hover_at(cx, cy, settle_time=0.4)
                    fresh_frame = capture.screenshot_numpy()
                    coords = read_game_coords(fresh_frame)
                    log_find(det, frame, grid_row=row, grid_col=col, coords=coords)

            tracker.mark_scanned(row, col)

            if col < cols - 1:
                pan_right(page, PAN_STEP_X)

        # End of row: pan down, reset horizontal position
        if row < rows - 1 and not _stop_flag:
            pan_down(page, PAN_STEP_Y)
            for _ in range(cols - 1):
                pan_left(page, PAN_STEP_X)
                time.sleep(0.05)

    return found_count


def run_cli():
    parser = argparse.ArgumentParser(description="Mercenary Exchange Finder")
    parser.add_argument("--reset", action="store_true", help="Clear saved scan state and start fresh")
    parser.add_argument("--gui", action="store_true", help="Launch control panel GUI")
    args = parser.parse_args()

    if args.gui:
        from ui.control_panel import launch_gui
        launch_gui()
        return

    print("=" * 60)
    print("  Mercenary Exchange Finder")
    print("=" * 60)

    cols = SCAN_COLS or 20
    rows = SCAN_ROWS or 15

    tracker = GridTracker(cols=cols, rows=rows)

    if args.reset:
        tracker.reset()
        print("[main] Scan state reset.")

    scanned, total = tracker.progress()
    if tracker.is_complete():
        print("[main] All cells already scanned. Run with --reset to start over.")
        return

    print(f"[main] Grid: {cols}x{rows} = {total} cells  ({scanned} already done)")
    print(f"[main] Log file: {get_log_path()}")
    print(f"[main] Connecting to Chrome at {CDP_URL} ...")

    try:
        page = capture.connect(CDP_URL)
    except ConnectionError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

    print("Connected. Press Ctrl+C to pause and save state.\n")
    signal.signal(signal.SIGINT, _handle_sigint)

    found = scan_grid(page, tracker, speed="Normal")

    if tracker.is_complete():
        print(f"\n[main] Scan complete. Found {found} Mercenary Exchange(s) this session.")
        print(f"[main] Run with --reset to scan again.")
    else:
        scanned, total = tracker.progress()
        print(f"\n[main] Paused at {scanned}/{total} cells. Run again to resume.")

    capture.disconnect()


if __name__ == "__main__":
    run_cli()
