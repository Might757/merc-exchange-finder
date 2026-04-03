# Mercenary Exchange Finder

A Python tool that automatically scans the Total Battle world map for Mercenary Exchanges and alerts you the moment one is found — before other players get there.

---

## How It Works

1. Attaches to your running Chrome browser via the debug port (no re-launch required)
2. Automatically pans across the world map in a configurable grid pattern
3. Takes a screenshot after each pan and scans it for the Mercenary Exchange icon using OpenCV template matching at multiple zoom scales
4. Confirms matches with OCR (looks for "Mercenary Exchange" text near the icon) to filter false positives
5. Moves the mouse over the found icon so the game displays the real K/X/Y coordinates, then reads them automatically
6. Alerts you with a sound and an on-screen popup — click anywhere on the popup to dismiss
7. Logs every find to a CSV file with timestamp, K/X/Y coordinates, confidence score, and an annotated screenshot

Scans are resumable — stop at any time and the next run picks up exactly where it left off.

---

## Requirements

- Python 3.10+
- Google Chrome

Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## First-Time Setup

### Step 1 — Capture a template image

The scanner needs a reference image of the Mercenary Exchange icon to search for. You only need to do this once.

```bash
python launcher.py        # open Chrome with the debug port
```

Log into Total Battle in the new Chrome window that opens. Navigate to the world map and find a Mercenary Exchange on screen (you can also find screenshots online and save a clean icon crop to `config/templates/` as a PNG manually).

Then run:

```bash
python capture_template.py
```

- A screenshot of the game will appear in a window
- Click and drag a rectangle tightly around the Mercenary Exchange icon
- Press **S** (or Enter) to save the crop as a template
- Press **R** to retake the screenshot, **Q** to quit

The template is saved to `config/templates/` automatically. You can save multiple templates (e.g. at different zoom levels) — the scanner uses all of them.

**Tips for a good template:**
- Crop tightly around the icon — minimal background
- Use a zoom level you'll actually scan at
- Avoid capturing the icon mid-animation if it has one
- A 40×40 to 80×80 pixel crop is ideal

### Step 2 — Launch the scanner

```bash
python main.py --gui
```

This opens the control panel. Make sure `launcher.py` is still running (Chrome must be open with the debug port active).

---

## Control Panel Guide

### Settings

| Setting | What it does | Recommended value |
|---|---|---|
| **Grid columns** | How many steps to scan horizontally before stopping | `20–30` depending on how far you want to cover |
| **Grid rows** | How many steps to scan vertically | `15–20` |
| **Start from col** | Skip the first N columns of the grid (useful to start mid-kingdom) | `0` unless starting partway in |
| **Start from row** | Skip the first N rows of the grid | `0` unless starting partway in |
| **Match threshold** | How similar a screen region must be to your template to count as a match. Lower = catches more but risks false positives. Higher = stricter but may miss faint icons | `0.78–0.82` for best results |
| **Scan speed** | Controls how fast the scanner pans and how long it waits for tiles to load | See speed guide below |
| **OCR confirmation** | After an icon match, reads the text near it to confirm it says "Mercenary Exchange". Reduces false positives but adds ~0.5s per cell | **On** for real scans |
| **Test mode** | Disables OCR keyword check — any icon match is accepted. Use this to verify the detection pipeline works with any template | **Off** for real scans |

### Scan Speed Guide

| Preset | Tile wait | Total time per cell | Notes |
|---|---|---|---|
| Slow | 1.0s | ~2s | Use if map tiles load slowly or you have a slow connection |
| Normal | 0.6s | ~1.2s | Default, works on most setups |
| Fast | 0.3s | ~0.6s | Recommended starting point — 2× faster than Normal |
| Fastest | 0.15s | ~0.3s | May miss icons if tiles load mid-screenshot. Test before relying on it |

Start with **Fast**. If you notice missed detections or blurry screenshots in the logs, step down to Normal.

### Start Position

The scanner always begins from wherever the map is currently positioned on screen. To scan a specific part of the kingdom:

1. Navigate the map in Total Battle to the area you want to start from
2. Set **Start from col** and **Start from row** to skip grid cells you don't need
3. Click **Start Scan**

The kingdom coordinate range is X: 0–511, Y: 0–1023. Not all of it is land — focus your scan on populated or active zones.

### Progress Bar

Shows how many grid cells have been scanned out of the total. The current adaptive threshold is shown below it — this auto-adjusts based on whether matches are confirmed or rejected by OCR.

### Found Exchanges Table

Displays all detected Mercenary Exchanges from the log file. **Click any row** to instantly copy the K/X/Y coordinates to your clipboard — a confirmation message appears at the bottom of the window.

### Buttons

| Button | Action |
|---|---|
| **▶ Start Scan** | Begins scanning from the current map position (or resumes if a previous scan was saved) |
| **■ Stop** | Stops after the current cell finishes and saves progress |
| **↺ Reset State** | Clears saved scan progress so the next scan starts fresh |

**Keyboard shortcut:** Press **F9** anywhere (even while the mouse is being moved) to stop the scan cleanly.

---

## Best Settings for Mercenary Exchange Detection

```
Match threshold:   0.80
Scan speed:        Fast
OCR confirmation:  On
OCR keywords:      mercenary, exchange, merc  (default, no change needed)
Test mode:         Off
Pan step X:        400px  (increase if your screen is larger than 1080p)
Pan step Y:        300px
```

If you're getting false positives (things that aren't exchanges showing up):
- Raise the threshold to `0.83–0.87`
- Make sure your template is a tight, clean crop of just the icon
- Keep OCR confirmation on

If you're missing exchanges that are clearly visible on screen:
- Lower the threshold to `0.70–0.75`
- Capture a new template at the exact zoom level you're scanning at
- Try Slow speed to ensure tiles fully load before the screenshot is taken

---

## Output

| Output | Location | Description |
|---|---|---|
| Alert popup | On screen | Floating window with coordinates when an exchange is found |
| Sound | System beep | Plays immediately on detection |
| CSV log | `logs/found_exchanges.csv` | Full history: timestamp, grid position, K/X/Y, confidence |
| Screenshots | `logs/screenshots/` | Annotated image for each find |
| Scan state | `scan_state.json` | Auto-managed — tracks which cells have been scanned |

---

## Troubleshooting

**"Could not connect to Chrome" / ECONNREFUSED**

Chrome only allows one process per user profile. If Chrome was already open when you ran `launcher.py`, the new window silently used the existing process (which has no debug port active).

The launcher creates a dedicated profile directory (`chrome_profile/`) to force a fully separate Chrome process. You do **not** need to close your existing Chrome. Just run `python launcher.py` and log into Total Battle in the new window that opens.

---

**No detections at all**

1. Make sure your template image is saved in `config/templates/` as a `.png` file
2. Check the template is a tight crop of the icon — too much background makes matching unreliable
3. Lower the threshold to `0.65` temporarily and enable Test Mode to verify the pipeline is working
4. Make sure you are at the same zoom level in-game as when you captured the template

---

**Too many false positives**

1. Raise the threshold to `0.85`
2. Make sure OCR confirmation is enabled
3. Recapture the template with a tighter crop and less background

---

**K/X/Y coordinates show `—` in the table**

The scanner reads coordinates by hovering the mouse over the found icon and OCR-ing the game's coordinate display. If this fails:
- The coordinate display may be in a non-standard position — set `COORD_REGION = (x1, y1, x2, y2)` in `config/settings.py` to point at the exact pixel area where Total Battle shows coordinates
- Make sure the game's coordinate bar is visible and not hidden by a menu

---

**Map is not panning correctly**

- Switch to Slow speed to give tiles more time to load
- Adjust `PAN_STEP_X` / `PAN_STEP_Y` in `config/settings.py` to match your screen resolution and zoom level

---

**EasyOCR is slow on first run**

EasyOCR downloads its language models (~300MB) the first time it runs. This is a one-time download and will not happen again.

---

## Project Structure

```
merc-exchange-finder/
├── main.py                  # Entry point (CLI and --gui flag)
├── launcher.py              # Launches Chrome with CDP debug port
├── capture_template.py      # Interactive tool to capture icon templates
├── scanner/
│   ├── capture.py           # Attaches to Chrome via Playwright CDP
│   ├── detector.py          # OpenCV template matching + EasyOCR + adaptive threshold
│   ├── navigator.py         # Map panning + hover-for-coordinates
│   ├── alert.py             # Sound + overlay popup
│   ├── grid_tracker.py      # Scan state persistence (resume support)
│   └── logger.py            # CSV logging + annotated screenshot saving
├── ui/
│   └── control_panel.py     # Tkinter GUI control panel
├── config/
│   ├── settings.py          # All configurable settings
│   └── templates/           # Icon template PNG files (add yours here)
└── logs/
    ├── found_exchanges.csv  # Created on first find
    └── screenshots/         # Annotated screenshots per find
```
