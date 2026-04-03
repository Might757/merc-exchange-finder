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
