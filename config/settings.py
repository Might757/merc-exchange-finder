"""
User-configurable settings for the Mercenary Exchange Finder.
Edit these values to match your setup before running.
"""

# --- Chrome CDP ---
# Launch Chrome with: chrome.exe --remote-debugging-port=9222
CDP_PORT = 9222
CDP_URL = f"http://localhost:{CDP_PORT}"

# --- Scanner ---
# Pixels to pan per step (adjust based on your screen resolution and map zoom)
PAN_STEP_X = 400       # horizontal pan distance per step (pixels)
PAN_STEP_Y = 300       # vertical pan distance per step (pixels)
# Speed presets — selected via the GUI dropdown.
# Each entry: (min_wait, max_wait, drag_duration, move_duration, pyautogui_pause)
#
# min_wait:  guaranteed pause after the drag before comparing frames
# max_wait:  ceiling — take the best frame if map hasn't settled by this time
# The scanner self-adjusts per cell: water settles fast, cities wait longer.
SPEED_PRESETS = {
    #              land_max  drag   move  pause
    "Slow":    (   3.0,     0.40,  0.15, 0.05 ),
    "Normal":  (   2.0,     0.30,  0.10, 0.05 ),
    "Fast":    (   1.5,     0.10,  0.05, 0.02 ),
    "Fastest": (   1.0,     0.02,  0.00, 0.01 ),
}

# How many columns and rows to scan before stopping (set to None for continuous loop)
SCAN_COLS = 20
SCAN_ROWS = 15

# --- Detection ---
# Minimum confidence (0.0–1.0) for OpenCV template match to count as a hit
MATCH_THRESHOLD = 0.75

# Run EasyOCR confirmation after an icon match? Slightly slower but reduces false positives.
USE_OCR_CONFIRMATION = True
OCR_CONFIRM_RADIUS = 80   # pixels around icon center to crop for OCR
OCR_KEYWORDS = ["mercenary", "exchange", "merc"]  # case-insensitive

# --- Template images ---
# Paths to icon template PNG files (relative to project root)
# Add multiple templates to handle slight visual variants
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "config", "templates")

# --- Game coordinate OCR ---
# Region of the screenshot where Total Battle displays K/X/Y coordinates.
# Set to a (x1, y1, x2, y2) tuple to target the exact area, or leave as None
# to automatically use the bottom 80 pixels of the viewport.
COORD_REGION = None

# Regex used to extract K, X, Y from OCR'd text.
# Matches patterns like: "K:5 X:123 Y:456" or "K 5, 123, 456"
import re
COORD_PATTERN = re.compile(r'[Kk]\s*[:\s]\s*(\d+)[^\d]+(\d+)[^\d]+(\d+)')

# --- Alert ---
ALERT_SOUND = True      # play a beep when found
ALERT_OVERLAY = True    # show Tkinter overlay window
