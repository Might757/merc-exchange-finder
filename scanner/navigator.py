"""
navigator.py — Pans the Total Battle world map by simulating mouse drag events.
"""

import time
import pyautogui
from playwright.sync_api import Page

pyautogui.PAUSE = 0.05

# Module-level timing vars — set by the scan worker before the loop starts
# so all pan_* helpers pick them up without needing extra parameters.
DRAG_DURATION = 0.3   # seconds for the drag gesture
MOVE_DURATION = 0.1   # seconds for the initial moveTo canvas center


def _get_canvas_center(page: Page) -> tuple[int, int]:
    try:
        canvas = page.query_selector("canvas")
        if canvas:
            box = canvas.bounding_box()
            if box:
                return int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2)
    except Exception:
        pass
    vp = page.viewport_size
    return vp["width"] // 2, vp["height"] // 2


def pan(page: Page, dx: int, dy: int):
    """
    Pan the map by dragging (dx, dy) pixels from the canvas centre.
    Uses module-level DRAG_DURATION and MOVE_DURATION.
    """
    cx, cy = _get_canvas_center(page)

    if MOVE_DURATION > 0:
        pyautogui.moveTo(cx, cy, duration=MOVE_DURATION)
    else:
        pyautogui.moveTo(cx, cy)

    pyautogui.mouseDown(button="left")

    if DRAG_DURATION > 0:
        pyautogui.moveTo(cx - dx, cy - dy, duration=DRAG_DURATION)
    else:
        pyautogui.moveTo(cx - dx, cy - dy)

    pyautogui.mouseUp(button="left")


def pan_right(page: Page, step: int):
    pan(page, step, 0)


def pan_left(page: Page, step: int):
    pan(page, -step, 0)


def pan_down(page: Page, step: int):
    pan(page, 0, step)


def pan_up(page: Page, step: int):
    pan(page, 0, -step)


def hover_at(screen_x: int, screen_y: int, settle_time: float = 0.4):
    """
    Move the mouse to (screen_x, screen_y) and wait for the game's coordinate
    display to update. Used to read accurate K/X/Y for a found icon.
    """
    if MOVE_DURATION > 0:
        pyautogui.moveTo(screen_x, screen_y, duration=MOVE_DURATION)
    else:
        pyautogui.moveTo(screen_x, screen_y)
    time.sleep(settle_time)
