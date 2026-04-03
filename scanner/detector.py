"""
detector.py — Detects Mercenary Exchange icons using OpenCV template matching,
with optional EasyOCR text confirmation.
"""

import os
import glob
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional

import config.settings as _settings

# Lazy-load EasyOCR reader (first init downloads models, ~300MB)
_ocr_reader = None

# Adaptive threshold state
_false_positive_streak = 0
_true_positive_streak = 0
_adaptive_threshold = _settings.MATCH_THRESHOLD
_ADAPT_STEP = 0.02
_MAX_THRESHOLD = 0.95
_MIN_THRESHOLD = 0.55
_STREAK_TRIGGER = 3


def get_adaptive_threshold() -> float:
    return _adaptive_threshold


def report_false_positive():
    global _false_positive_streak, _true_positive_streak, _adaptive_threshold
    _false_positive_streak += 1
    _true_positive_streak = 0
    if _false_positive_streak >= _STREAK_TRIGGER:
        old = _adaptive_threshold
        _adaptive_threshold = min(_MAX_THRESHOLD, _adaptive_threshold + _ADAPT_STEP)
        if _adaptive_threshold != old:
            print(f"[detector] Adaptive threshold raised: {old:.2f} → {_adaptive_threshold:.2f} "
                  f"({_false_positive_streak} consecutive false positives)")
        _false_positive_streak = 0


def report_true_positive():
    global _true_positive_streak, _false_positive_streak, _adaptive_threshold
    _true_positive_streak += 1
    _false_positive_streak = 0
    if _true_positive_streak >= _STREAK_TRIGGER:
        old = _adaptive_threshold
        _adaptive_threshold = max(_MIN_THRESHOLD, _adaptive_threshold - _ADAPT_STEP)
        if _adaptive_threshold != old:
            print(f"[detector] Adaptive threshold lowered: {old:.2f} → {_adaptive_threshold:.2f} "
                  f"({_true_positive_streak} consecutive true positives)")
        _true_positive_streak = 0


@dataclass
class Detection:
    x: int
    y: int
    w: int
    h: int
    confidence: float
    confirmed_by_ocr: Optional[bool] = None

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)


def _load_templates() -> list[np.ndarray]:
    paths = glob.glob(os.path.join(_settings.TEMPLATES_DIR, "*.png"))
    templates = []
    for path in paths:
        tmpl = cv2.imread(path, cv2.IMREAD_COLOR)
        if tmpl is not None:
            templates.append(tmpl)
            print(f"[detector] Loaded template: {os.path.basename(path)}")
    if not templates:
        print(f"[detector] WARNING: No templates found in {_settings.TEMPLATES_DIR}")
    return templates


def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        print("[detector] Initialising EasyOCR (first run downloads models)...")
        _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _ocr_reader


def _ocr_confirm(frame: np.ndarray, cx: int, cy: int) -> bool:
    """
    Crop a region around (cx, cy) and run OCR to check for Mercenary Exchange text.
    Reads OCR_CONFIRM_RADIUS and OCR_KEYWORDS dynamically from settings so GUI
    overrides propagate correctly.
    """
    h, w = frame.shape[:2]
    r = _settings.OCR_CONFIRM_RADIUS
    x1, y1 = max(0, cx - r), max(0, cy - r)
    x2, y2 = min(w, cx + r), min(h, cy + r)
    crop = frame[y1:y2, x1:x2]

    reader = _get_ocr_reader()
    results = reader.readtext(crop, detail=0)
    combined = " ".join(results).lower()
    return any(kw in combined for kw in _settings.OCR_KEYWORDS)


def read_game_coords(frame: np.ndarray) -> tuple[int, int, int] | None:
    """
    OCR the coordinate display area of the game screenshot.
    Returns (K, X, Y) as integers, or None if coordinates cannot be read.

    Total Battle shows coordinates somewhere on the map UI (usually a bar at the
    bottom or top of the canvas). COORD_REGION in settings can be set to a
    (x1, y1, x2, y2) tuple to target the exact area; defaults to the bottom 80px.
    """
    h, w = frame.shape[:2]
    region = _settings.COORD_REGION

    if region is not None:
        x1, y1, x2, y2 = region
        crop = frame[y1:y2, x1:x2]
    else:
        # Default: bottom 80 pixels of the frame
        crop = frame[max(0, h - 80):h, 0:w]

    reader = _get_ocr_reader()
    results = reader.readtext(crop, detail=0)
    text = " ".join(results)
    print(f"[detector] Coord OCR raw text: {text!r}")

    match = _settings.COORD_PATTERN.search(text)
    if match:
        k, x, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        print(f"[detector] Game coords: K={k} X={x} Y={y}")
        return k, x, y

    print("[detector] Could not parse K/X/Y from coordinate area.")
    return None


def _multi_scale_match(frame: np.ndarray, template: np.ndarray, threshold: float) -> list[Detection]:
    detections = []
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    for scale in [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]:
        tmpl_scaled = cv2.resize(
            template,
            (max(1, int(template.shape[1] * scale)), max(1, int(template.shape[0] * scale))),
            interpolation=cv2.INTER_AREA,
        )
        gray_tmpl = cv2.cvtColor(tmpl_scaled, cv2.COLOR_BGR2GRAY)
        th, tw = gray_tmpl.shape[:2]

        if th > gray_frame.shape[0] or tw > gray_frame.shape[1]:
            continue

        result = cv2.matchTemplate(gray_frame, gray_tmpl, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)

        for pt in zip(*locations[::-1]):
            detections.append(Detection(
                x=int(pt[0]), y=int(pt[1]),
                w=tw, h=th,
                confidence=float(result[pt[1], pt[0]]),
            ))

    return _non_max_suppression(detections)


def _non_max_suppression(detections: list[Detection], overlap_thresh: float = 0.4) -> list[Detection]:
    if not detections:
        return []

    detections = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept = []

    for det in detections:
        cx, cy = det.center
        duplicate = False
        for k in kept:
            kx, ky = k.center
            if abs(cx - kx) < det.w * (1 - overlap_thresh) and abs(cy - ky) < det.h * (1 - overlap_thresh):
                duplicate = True
                break
        if not duplicate:
            kept.append(det)

    return kept


def detect(frame: np.ndarray) -> tuple[list[Detection], int]:
    """
    Run full detection pipeline on a BGR frame.
    Uses current adaptive threshold and reads USE_OCR_CONFIRMATION dynamically
    from settings so GUI overrides propagate correctly.

    Returns (confirmed_detections, raw_match_count) so the caller can
    surface "matched but OCR rejected" warnings in the UI.
    """
    templates = _load_templates()
    if not templates:
        return [], 0

    threshold = get_adaptive_threshold()
    all_detections: list[Detection] = []

    for tmpl in templates:
        matches = _multi_scale_match(frame, tmpl, threshold)
        all_detections.extend(matches)

    if not all_detections:
        return [], 0

    all_detections = _non_max_suppression(all_detections)
    raw_count = len(all_detections)

    # Read setting dynamically so GUI checkbox changes take effect immediately
    if not _settings.USE_OCR_CONFIRMATION:
        for _ in all_detections:
            report_true_positive()
        return all_detections, raw_count

    confirmed = []
    for det in all_detections:
        cx, cy = det.center
        det.confirmed_by_ocr = _ocr_confirm(frame, cx, cy)
        if det.confirmed_by_ocr:
            confirmed.append(det)
            report_true_positive()
        else:
            print(f"[detector] Icon match at {det.center} rejected by OCR (conf={det.confidence:.2f})")
            report_false_positive()

    return confirmed, raw_count


def draw_detections(frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
    out = frame.copy()
    for det in detections:
        cv2.rectangle(out, (det.x, det.y), (det.x + det.w, det.y + det.h), (0, 255, 0), 2)
        label = f"{det.confidence:.2f}"
        cv2.putText(out, label, (det.x, det.y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return out
