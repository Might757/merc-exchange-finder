"""
capture_template.py — Interactive tool to capture a Mercenary Exchange icon template.

Run this while Chrome is open with Total Battle on the world map,
with a Mercenary Exchange visible on screen.

Usage:
    python capture_template.py

Controls:
    - A window will show the current game screenshot
    - Click and drag to draw a rectangle around the icon
    - Press ENTER or S to save the cropped region as a template
    - Press R to retake the screenshot
    - Press Q to quit
"""

import os
import cv2
import numpy as np
import datetime

import scanner.capture as capture
from config.settings import CDP_URL, TEMPLATES_DIR

# Mouse drag state
_drawing = False
_start = (-1, -1)
_end = (-1, -1)
_rect_img = None
_base_img = None


def _mouse_cb(event, x, y, flags, param):
    global _drawing, _start, _end, _rect_img

    if event == cv2.EVENT_LBUTTONDOWN:
        _drawing = True
        _start = (x, y)
        _end = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE and _drawing:
        _end = (x, y)
        _rect_img = _base_img.copy()
        cv2.rectangle(_rect_img, _start, _end, (0, 255, 0), 2)

    elif event == cv2.EVENT_LBUTTONUP:
        _drawing = False
        _end = (x, y)
        _rect_img = _base_img.copy()
        cv2.rectangle(_rect_img, _start, _end, (0, 255, 0), 2)


def main():
    global _base_img, _rect_img, _start, _end

    print("[capture_template] Connecting to Chrome...")
    try:
        page = capture.connect(CDP_URL)
    except ConnectionError as e:
        print(f"[ERROR] {e}")
        return

    os.makedirs(TEMPLATES_DIR, exist_ok=True)

    while True:
        print("\n[capture_template] Taking screenshot... (navigate to a Mercenary Exchange in-game first)")
        _base_img = capture.screenshot_numpy()
        _rect_img = _base_img.copy()
        _start = (-1, -1)
        _end = (-1, -1)

        win = "Template Capture — Drag to select icon, S=Save, R=Retake, Q=Quit"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, 1280, 720)
        cv2.setMouseCallback(win, _mouse_cb)

        print("[capture_template] Drag a rectangle around the Mercenary Exchange icon.")
        print("  S = save selection as template")
        print("  R = retake screenshot")
        print("  Q = quit")

        while True:
            display = _rect_img if _rect_img is not None else _base_img
            cv2.imshow(win, display)
            key = cv2.waitKey(30) & 0xFF

            if key == ord("q"):
                cv2.destroyAllWindows()
                capture.disconnect()
                print("[capture_template] Done.")
                return

            elif key == ord("r"):
                cv2.destroyAllWindows()
                break  # retake

            elif key in (ord("s"), 13):  # S or Enter
                x1 = min(_start[0], _end[0])
                y1 = min(_start[1], _end[1])
                x2 = max(_start[0], _end[0])
                y2 = max(_start[1], _end[1])

                if x2 - x1 < 5 or y2 - y1 < 5:
                    print("[capture_template] Selection too small. Try again.")
                    continue

                crop = _base_img[y1:y2, x1:x2]
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(TEMPLATES_DIR, f"merc_exchange_{ts}.png")
                cv2.imwrite(filename, crop)
                print(f"[capture_template] Template saved: {filename}")
                print(f"[capture_template] Size: {crop.shape[1]}x{crop.shape[0]} pixels")

                # Show the saved crop
                cv2.imshow("Saved Template (press any key)", crop)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

                another = input("Capture another template? (y/n): ").strip().lower()
                if another != "y":
                    capture.disconnect()
                    return
                break


if __name__ == "__main__":
    main()
