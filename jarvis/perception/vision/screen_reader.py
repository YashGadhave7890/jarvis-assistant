"""
Screen Reader & Visual Perception Module for Jarvis.
Captures high-resolution desktop snapshots, extracts active window hierarchy,
and prepares visual context for the HUD and agents.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

CAPTURES_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "static" / "captures"


try:
    from core.capabilities import has_display, NO_SCREEN_MSG
except ImportError:
    def has_display():
        if sys.platform == "win32":
            return True
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    NO_SCREEN_MSG = "Screen reading is available only when Jarvis is running on a local graphical desktop."


def is_graphical_desktop_available() -> bool:
    """
    Checks whether a local graphical desktop display session is available.
    Delegates to centralized capability detection.
    """
    return has_display()


class ScreenReader:
    def __init__(self):
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        self.is_headless = not is_graphical_desktop_available()
        if self.is_headless:
            logger.info("ScreenReader perception module initialized in headless mode (no graphical display).")
        else:
            logger.info("ScreenReader perception module initialized with local graphical desktop.")

    async def capture_screen(self, filename: str = "screen_latest.jpg") -> dict:
        """Captures primary monitor and saves to static captures directory."""
        return await asyncio.to_thread(self._sync_capture, filename)

    def _sync_capture(self, filename: str) -> dict:
        if self.is_headless or not is_graphical_desktop_available():
            logger.debug(f"Screen capture skipped: {NO_SCREEN_MSG}")
            return {
                "success": False,
                "error": NO_SCREEN_MSG,
                "message": NO_SCREEN_MSG,
                "active_window": "Desktop",
                "open_windows": [],
                "web_url": "",
            }

        try:
            # Lazy import pyautogui only when a graphical desktop session is available
            import pyautogui

            target_path = CAPTURES_DIR / filename
            screenshot = pyautogui.screenshot()
            # Resize if 4K to save memory and load faster
            if screenshot.width > 1920:
                screenshot = screenshot.resize(
                    (1920, int(1920 * screenshot.height / screenshot.width)),
                    Image.Resampling.LANCZOS,
                )
            screenshot.save(str(target_path), "JPEG", quality=82)

            active_win = self.get_active_window_title()
            open_wins = self.get_open_windows()

            logger.info(f"Screenshot saved to {target_path}, active window: '{active_win}'")
            return {
                "success": True,
                "file_path": str(target_path),
                "web_url": f"/static/captures/{filename}",
                "active_window": active_win,
                "open_windows": open_wins[:6],
                "resolution": f"{screenshot.width}x{screenshot.height}",
            }
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Screen reading is available only when Jarvis is running on a local graphical desktop.",
                "active_window": "Desktop",
                "open_windows": [],
                "web_url": "",
            }

    def get_active_window_title(self) -> str:
        if self.is_headless or sys.platform != "win32":
            return "Desktop"
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd).strip()
            return title if title else "Desktop"
        except Exception:
            return "Active Desktop"

    def get_open_windows(self) -> list:
        if self.is_headless or sys.platform != "win32":
            return []
        windows = []
        try:
            import win32gui
            def enum_cb(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    txt = win32gui.GetWindowText(hwnd).strip()
                    if txt and txt not in ["Program Manager", "Settings", "Default IME"]:
                        windows.append(txt)
            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass
        return windows
