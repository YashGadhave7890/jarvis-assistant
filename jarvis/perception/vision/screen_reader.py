"""
Screen Reader & Visual Perception Module for Jarvis.
Captures high-resolution desktop snapshots, extracts active window hierarchy,
and prepares visual context for the HUD and agents.
"""

import asyncio
import logging
import os
from pathlib import Path
from PIL import Image
import pyautogui

logger = logging.getLogger(__name__)

CAPTURES_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "static" / "captures"


class ScreenReader:
    def __init__(self):
        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("ScreenReader perception module initialized.")

    async def capture_screen(self, filename: str = "screen_latest.jpg") -> dict:
        """Captures primary monitor and saves to static captures directory."""
        return await asyncio.to_thread(self._sync_capture, filename)

    def _sync_capture(self, filename: str) -> dict:
        try:
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
                "active_window": "Desktop",
                "open_windows": [],
                "web_url": "",
            }

    def get_active_window_title(self) -> str:
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd).strip()
            return title if title else "Desktop"
        except Exception:
            return "Active Desktop"

    def get_open_windows(self) -> list:
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
