"""
logger.py — Logs found Mercenary Exchanges to a CSV file and saves
annotated screenshots of each find.
"""

import csv
import os
import datetime
import cv2

from scanner.detector import Detection, draw_detections

_LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "logs",
)
_LOG_FILE = os.path.join(_LOG_DIR, "found_exchanges.csv")
_SCREENSHOT_DIR = os.path.join(_LOG_DIR, "screenshots")

_CSV_HEADERS = ["timestamp", "grid_row", "grid_col", "screen_x", "screen_y", "k_coord", "x_coord", "y_coord", "confidence", "ocr_confirmed", "screenshot"]


def _ensure_dirs():
    os.makedirs(_SCREENSHOT_DIR, exist_ok=True)
    if not os.path.exists(_LOG_FILE):
        with open(_LOG_FILE, "w", newline="") as f:
            csv.writer(f).writerow(_CSV_HEADERS)


def log_find(detection: Detection, frame, grid_row: int = -1, grid_col: int = -1,
             coords: tuple | None = None):
    """
    Record a found Mercenary Exchange to CSV and save an annotated screenshot.

    Args:
        detection: the Detection object from detector.py
        frame:     the BGR numpy frame in which it was found
        grid_row:  which grid row was being scanned (-1 if unknown)
        grid_col:  which grid col was being scanned (-1 if unknown)
        coords:    (K, X, Y) game coordinates from OCR, or None if not found
    """
    _ensure_dirs()

    ts = datetime.datetime.now()
    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
    ts_file = ts.strftime("%Y%m%d_%H%M%S")

    # Save annotated screenshot
    annotated = draw_detections(frame, [detection])
    screenshot_name = f"found_{ts_file}_r{grid_row}c{grid_col}.png"
    screenshot_path = os.path.join(_SCREENSHOT_DIR, screenshot_name)
    cv2.imwrite(screenshot_path, annotated)

    cx, cy = detection.center
    k, x, y = coords if coords else ("", "", "")
    row_data = [
        ts_str,
        grid_row,
        grid_col,
        cx,
        cy,
        k,
        x,
        y,
        f"{detection.confidence:.4f}",
        detection.confirmed_by_ocr,
        screenshot_name,
    ]

    with open(_LOG_FILE, "a", newline="") as f:
        csv.writer(f).writerow(row_data)

    print(f"[logger] Logged find → {_LOG_FILE}")
    print(f"[logger] Screenshot → {screenshot_path}")


def get_log_path() -> str:
    return _LOG_FILE


def get_all_finds() -> list[dict]:
    """Return all logged finds as a list of dicts."""
    if not os.path.exists(_LOG_FILE):
        return []
    with open(_LOG_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)
