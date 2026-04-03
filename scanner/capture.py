"""
capture.py — Attaches to an existing Chrome session via CDP and captures screenshots.

Chrome must be launched with: --remote-debugging-port=9222
  Use launcher.py — it handles finding Chrome and opening it with the right flags.
"""

import time
import numpy as np
from playwright.sync_api import sync_playwright, Browser, Page


_playwright = None
_browser: Browser = None
_page: Page = None


def _wait_for_port(cdp_url: str, timeout: float = 15.0, poll: float = 0.5) -> bool:
    """
    Poll Chrome's CDP HTTP endpoint until it responds or timeout is reached.
    Returns True if the port is ready, False if it timed out.
    This prevents connect_over_cdp from hanging indefinitely.
    """
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{cdp_url}/json/version", timeout=2)
            return True
        except Exception:
            time.sleep(poll)
    return False


def connect(cdp_url: str = "http://localhost:9222") -> Page:
    """
    Attach to a running Chrome session via CDP.
    Returns the first usable page (tab).
    Raises ConnectionError with a clear message if Chrome is not reachable.
    """
    global _playwright, _browser, _page

    print(f"[capture] Checking Chrome debug port at {cdp_url} ...")
    if not _wait_for_port(cdp_url, timeout=15.0):
        raise ConnectionError(
            f"Chrome is not responding on {cdp_url} after 15 seconds.\n\n"
            f"Most likely causes:\n"
            f"  1. launcher.py is not running — start it first and keep the terminal open\n"
            f"  2. Chrome opened but failed to bind the debug port (another Chrome may be using it)\n"
            f"  3. A firewall is blocking localhost port 9222\n\n"
            f"To rule out the firewall: open a browser and visit {cdp_url}/json/version\n"
            f"If you see JSON data, Chrome is ready. If not, check Windows Firewall settings."
        )

    print(f"[capture] Port ready. Connecting via Playwright CDP ...")
    try:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.connect_over_cdp(cdp_url)
    except Exception as e:
        raise ConnectionError(
            f"Could not connect to Chrome at {cdp_url}.\n"
            f"Original error: {e}"
        )

    # Prefer the Total Battle tab; fall back to first non-devtools tab
    for context in _browser.contexts:
        for page in context.pages:
            url = page.url.lower()
            if "devtools" not in url:
                if "totalbattle" in url or "total-battle" in url or "plarium" in url:
                    _page = page
                    print(f"[capture] Connected to game tab: {page.url}")
                    return _page

    for context in _browser.contexts:
        for page in context.pages:
            if "devtools" not in page.url.lower():
                _page = page
                print(f"[capture] Connected to tab: {page.url}")
                return _page

    raise ConnectionError(
        "Chrome is running but no usable tab was found.\n"
        "Make sure Total Battle is open in the Chrome window that launcher.py opened."
    )


def screenshot_numpy() -> np.ndarray:
    if _page is None:
        raise RuntimeError("Not connected. Call connect() first.")

    png_bytes = _page.screenshot(full_page=False)
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    arr = np.array(img)
    return arr[:, :, ::-1].copy()


# Pixel std dev (at 1/8 scale) below this → water / empty area.
# Water in Total Battle is a near-uniform teal/blue (~std 3–8).
# Land with buildings and icons is typically std 20–60+.
_WATER_COMPLEXITY_THRESHOLD = 12.0


def _frame_complexity(frame: np.ndarray) -> float:
    """
    Measure visual complexity of a BGR frame using pixel std dev at 1/8 scale.
    Water/empty → low (~3–8). Land with icons/buildings → high (~20–60+).
    """
    import cv2
    small = cv2.resize(frame, (frame.shape[1] // 8, frame.shape[0] // 8))
    return float(small.astype(np.float32).std())


def _frames_are_stable(a: np.ndarray, b: np.ndarray, threshold: float = 0.96) -> bool:
    """True if two frames are sufficiently similar (tiles have stopped loading)."""
    import cv2
    small_a = cv2.resize(a, (a.shape[1] // 8, a.shape[0] // 8))
    small_b = cv2.resize(b, (b.shape[1] // 8, b.shape[0] // 8))
    diff = np.abs(small_a.astype(np.float32) - small_b.astype(np.float32))
    return 1.0 - (diff.mean() / 255.0) >= threshold


def wait_for_stable_frame(
    drag_duration: float = 0.3,
    land_max_wait: float = 2.0,
    poll_interval: float = 0.12,
) -> np.ndarray:
    """
    Two-phase wait after a map pan:

    Phase 1 — Drag settle (fixed):
        Wait drag_duration + 0.1s. Guarantees the mouse gesture has physically
        finished and the map has stopped moving before we look at it.

    Phase 2 — Content detection (adaptive):
        Measure visual complexity of the settled frame.
        - Low complexity (water/empty) → return immediately. Fast.
        - High complexity (land/city)  → compare consecutive frames until tiles
          stop changing, or land_max_wait is exhausted. Correct.
    """
    time.sleep(drag_duration + 0.1)
    settled = screenshot_numpy()

    if _frame_complexity(settled) < _WATER_COMPLEXITY_THRESHOLD:
        return settled  # water — nothing to wait for

    # Land: wait until rendering settles
    prev = settled
    deadline = time.time() + land_max_wait
    while time.time() < deadline:
        time.sleep(poll_interval)
        curr = screenshot_numpy()
        if _frames_are_stable(prev, curr):
            return curr
        prev = curr

    return prev  # timed out — return best available frame


def get_page() -> Page:
    if _page is None:
        raise RuntimeError("Not connected. Call connect() first.")
    return _page


def disconnect():
    global _playwright, _browser, _page
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
    _browser = None
    _page = None
    _playwright = None
