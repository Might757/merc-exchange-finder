"""
capture.py — Attaches to an existing Chrome session via CDP and captures screenshots.

Chrome must be launched with: --remote-debugging-port=9222
  Windows: chrome.exe --remote-debugging-port=9222
  Or use the launcher.py helper script included in this project.
"""

import numpy as np
from playwright.sync_api import sync_playwright, Browser, Page


_playwright = None
_browser: Browser = None
_page: Page = None


def connect(cdp_url: str = "http://localhost:9222") -> Page:
    """
    Attach to a running Chrome session via CDP.
    Returns the first page (tab) that is not a DevTools page.
    Raises ConnectionError if Chrome is not reachable.
    """
    global _playwright, _browser, _page

    try:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.connect_over_cdp(cdp_url)
    except Exception as e:
        raise ConnectionError(
            f"Could not connect to Chrome at {cdp_url}.\n"
            f"Make sure Chrome is running with --remote-debugging-port=9222\n"
            f"Original error: {e}"
        )

    # Find the Total Battle game tab (prefer it, fall back to first non-devtools page)
    for context in _browser.contexts:
        for page in context.pages:
            url = page.url.lower()
            if "devtools" not in url:
                if "totalbattle" in url or "total-battle" in url or "plarium" in url:
                    _page = page
                    print(f"[capture] Connected to game tab: {page.url}")
                    return _page

    # Fallback: first non-devtools page
    for context in _browser.contexts:
        for page in context.pages:
            if "devtools" not in page.url.lower():
                _page = page
                print(f"[capture] Connected to tab: {page.url}")
                return _page

    raise ConnectionError("No usable browser tab found. Make sure Total Battle is open in Chrome.")


def screenshot_numpy() -> np.ndarray:
    """
    Capture a screenshot of the current page and return it as a BGR numpy array
    suitable for OpenCV processing.
    """
    if _page is None:
        raise RuntimeError("Not connected. Call connect() first.")

    png_bytes = _page.screenshot(full_page=False)
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    arr = np.array(img)
    # PIL gives RGB, OpenCV expects BGR
    return arr[:, :, ::-1].copy()


def get_page() -> Page:
    """Return the currently connected Playwright page."""
    if _page is None:
        raise RuntimeError("Not connected. Call connect() first.")
    return _page


def disconnect():
    """Clean up Playwright resources."""
    global _playwright, _browser, _page
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
    _browser = None
    _page = None
    _playwright = None
