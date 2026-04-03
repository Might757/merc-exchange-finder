# Mercenary Exchange Finder — Plan

## Context
Total Battle browser game (Chrome). The world map is a large 2D canvas the player navigates manually.
Mercenary Exchanges appear as icons on the map, with a text label visible on interaction/zoom.
The search area spans entire kingdoms — huge. Goal: auto-scan and alert the player when one is found.

---

## Architecture Overview

**Stack:** Python, Playwright (browser control), OpenCV (icon detection), EasyOCR (text confirmation), PyAutoGUI (mouse/keyboard input), Tkinter (overlay alert UI)

**Approach:**
- Attach Playwright to the existing Chrome session (via CDP remote debugging port)
- Systematically pan the map using simulated mouse drags or keyboard navigation
- After each pan step, capture a screenshot of the game canvas
- Run OpenCV template matching against known Mercenary Exchange icon templates
- If a match is found above confidence threshold, optionally confirm with EasyOCR
- Alert the user (sound + on-screen overlay) so they can click it themselves

**Why Playwright over raw screen capture:**
- Cleaner screenshot API tied to the browser window, not desktop position
- Can attach to an already-running Chrome session (no need to re-launch)
- Resilient to window resizing or moving

---

## File Structure

```
merc-exchange-finder/
├── main.py                    # Entry point — starts scanner loop
├── launcher.py                # Launches Chrome with CDP port enabled
├── capture_template.py        # Interactive tool to save icon templates
├── scanner/
│   ├── __init__.py
│   ├── capture.py             # Screenshot via Playwright CDP
│   ├── detector.py            # OpenCV template match + EasyOCR confirm
│   ├── navigator.py           # Map pan/scroll automation logic
│   └── alert.py               # Sound + overlay alert
├── config/
│   ├── settings.py            # Scan region, sensitivity, step size, CDP port
│   └── templates/             # Reference icon images (PNG crops of Merc Exchange)
├── tasks/
│   ├── todo.md                # This file
│   └── lessons.md
└── requirements.txt
```

---

## Implementation Plan

### Phase 1 — Foundation
- [x] 1.1 Set up project structure and `requirements.txt`
- [x] 1.2 Implement `capture.py` — attach to Chrome via CDP, take canvas screenshot
- [x] 1.3 Implement `navigator.py` — simulate map pan (mouse drag left/right/up/down by configurable step)
- [x] 1.4 Implement `detector.py` — load template images, run `cv2.matchTemplate`, return matches above threshold
- [x] 1.5 Implement `alert.py` — play sound + show Tkinter overlay with match coordinates
- [x] 1.6 Implement `main.py` — orchestrate the scan loop: screenshot → detect → pan → repeat

### Phase 2 — Smarter Detection
- [x] 2.1 Multi-scale template matching (handle zoom level differences) — in detector.py
- [x] 2.2 EasyOCR secondary confirmation — after icon match, OCR the surrounding area for "Mercenary" text
- [x] 2.3 Scan grid tracking — `scanner/grid_tracker.py` persists scanned cells to `scan_state.json`; resumable across sessions
- [x] 2.4 Adaptive confidence threshold — auto-raises on consecutive false positives, lowers on confirmed finds

### Phase 3 — UX & Config
- [x] 3.1 Tkinter control panel — `ui/control_panel.py`; start/stop, settings, live progress bar, finds table
- [x] 3.2 `settings.py` — user-configurable: CDP port, scan step size, match threshold, template paths
- [x] 3.3 Template capture tool — `capture_template.py` lets user crop + save icon from live screenshot
- [x] 3.4 Logging — `scanner/logger.py` writes CSV + annotated screenshots to `logs/`

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Browser control | Playwright CDP attach | No re-launch needed, works with existing session |
| Icon detection | OpenCV template match | Faster and more accurate than pure OCR for icons |
| Text confirm | EasyOCR | Lightweight, good accuracy, no Tesseract install friction |
| UI | Tkinter overlay | Built into Python stdlib, minimal dependency |
| Panning | Mouse drag simulation | Works regardless of game's keyboard shortcuts |

---

## Open Questions / Assumptions
- We assume the Mercenary Exchange icon is visually consistent (same sprite) across zoom levels — Phase 2 handles zoom variation
- Chrome must be launched with `--remote-debugging-port=9222` for CDP attach (launcher.py handles this)
- Template images must be captured manually from a real game session using capture_template.py

---

## Review
All phases complete. Full pipeline: Chrome CDP → screenshot → multi-scale OpenCV detect → EasyOCR confirm →
adaptive threshold → grid tracker (resumable) → alert (sound + overlay) → CSV log + annotated screenshots → Tkinter GUI.
