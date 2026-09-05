"""
Advanced Desktop Automation — pyautogui, subprocess, webbrowser, volume control,
screenshot, clipboard, window management, and rich app launching.
"""

import asyncio
import logging
import os
import subprocess
import sys
import webbrowser
import urllib.parse
import urllib.request
import re
import time
from difflib import SequenceMatcher
from core.event_bus import EventBus

try:
    from core.capabilities import has_desktop_automation, has_display, NO_DESKTOP_MSG
except ImportError:
    def has_desktop_automation():
        return sys.platform == "win32"
    def has_display():
        return sys.platform == "win32" or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    NO_DESKTOP_MSG = "Desktop application management is only available when running Jarvis locally on your Windows machine, sir."

logger = logging.getLogger(__name__)


# ── Helpers to locate common Windows apps ──────────────────────────────────────
def _find_chrome() -> str:
    for p in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]:
        if os.path.exists(p):
            return p
    return "chrome.exe"


def _find_vscode() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local_app_data, r"Programs\Microsoft VS Code\Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
        "code.cmd",
        "code.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "code.cmd"


def _find_cursor() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local_app_data, r"Programs\cursor\Cursor.exe"),
        os.path.join(local_app_data, r"Programs\cursor\resources\app\codeBin\code.cmd"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "cursor.exe"


def _find_windsurf() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    p = os.path.join(local_app_data, r"Programs\Windsurf\Windsurf.exe")
    if os.path.exists(p):
        return p
    return "windsurf.exe"


# ── App catalogue ──────────────────────────────────────────────────────────────
_APPS = {
    "notepad":      {"keywords": ["notepad", "note pad", "notes", "text editor"],  "exe": "notepad.exe"},
    "calculator":   {"keywords": ["calculator", "calc", "math", "calculate"],       "exe": "calc.exe"},
    "chrome":       {"keywords": ["chrome", "google chrome", "browser"],            "exe": _find_chrome()},
    "vs code":      {"keywords": ["vs code", "vscode", "visual studio code", "code"], "exe": _find_vscode()},
    "cursor":       {"keywords": ["cursor", "cursor ide"],                          "exe": _find_cursor()},
    "windsurf":     {"keywords": ["windsurf", "windsurf ide"],                      "exe": _find_windsurf()},
    "firefox":      {"keywords": ["firefox", "mozilla"],                            "exe": "firefox.exe"},
    "explorer":     {"keywords": ["explorer", "file explorer", "files", "folder"],  "exe": "explorer.exe"},
    "cmd":          {"keywords": ["cmd", "command prompt", "terminal", "console"],  "exe": "cmd.exe"},
    "powershell":   {"keywords": ["powershell"],                                    "exe": "powershell.exe"},
    "paint":        {"keywords": ["paint", "ms paint", "draw"],                     "exe": "mspaint.exe"},
    "word":         {"keywords": ["word", "microsoft word", "document", "doc"],     "exe": "winword.exe"},
    "excel":        {"keywords": ["excel", "spreadsheet", "sheets"],                "exe": "excel.exe"},
    "powerpoint":   {"keywords": ["powerpoint", "presentation", "slides"],          "exe": "powerpnt.exe"},
    "spotify":      {"keywords": ["spotify"],                                       "exe": "spotify.exe"},
    "task manager": {"keywords": ["task manager", "taskmgr"],                       "exe": "taskmgr.exe"},
    "settings":     {"keywords": ["settings", "preferences"],                       "exe": "ms-settings:"},
    "clock":        {"keywords": ["clock", "alarm"],                                "exe": "ms-clock:"},
    "snipping tool":{"keywords": ["snipping tool", "snip"],                         "exe": "snippingtool.exe"},
    "youtube":      {"keywords": ["youtube", "yt"],                                  "exe": "https://www.youtube.com"},
    "google":       {"keywords": ["google"],                                         "exe": "https://www.google.com"},
}


class DesktopAutomation:
    """
    High-level desktop automation: launch/close apps, web, YouTube,
    type text, screenshot, volume, clipboard.
    """

    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self._gui = None
        if has_desktop_automation() or has_display():
            try:
                import pyautogui
                pyautogui.FAILSAFE = False
                pyautogui.PAUSE    = 0.05
                self._gui = pyautogui
            except (ImportError, KeyError, Exception) as e:
                self._gui = None
                logger.warning(f"pyautogui initialization skipped ({e}) — GUI automation disabled.")
        logger.info("DesktopAutomation initialized.")

    # ── Application control ───────────────────────────────────────────────────
    async def launch_app(self, app_name: str) -> str:
        """Detect and launch an app by fuzzy name match or Windows shell. Returns spoken reply."""
        if not has_desktop_automation():
            return NO_DESKTOP_MSG

        name_l = app_name.lower().strip()
        match  = self._detect_app(name_l)
        if match:
            exe = _APPS[match]["exe"]
            logger.info(f"Launching '{match}' → {exe}")
            try:
                # Direct startfile handles exes, ms-uris, and URLs seamlessly
                os.startfile(exe)
                return f"Opening {match.title()} for you, sir."
            except Exception as e:
                logger.warning(f"os.startfile failed for {exe}: {e}. Trying Popen...")
                try:
                    subprocess.Popen([exe], shell=True)
                    return f"Opening {match.title()} for you, sir."
                except Exception as e2:
                    logger.warning(f"Popen failed: {e2}. Trying shell start...")
                    try:
                        subprocess.Popen(f'start "" "{exe}"', shell=True)
                        return f"Opening {match.title()} for you, sir."
                    except Exception:
                        pass

        # Try direct Windows start command as fallback
        clean_name = name_l.replace("open", "").replace("launch", "").replace("start", "").strip()
        for candidate in [clean_name, f"{clean_name}.exe"]:
            if candidate:
                try:
                    os.startfile(candidate)
                    return f"Opening {clean_name.title()} for you, sir."
                except Exception:
                    pass
                try:
                    subprocess.Popen(f'start {candidate}', shell=True)
                    return f"Opening {clean_name.title()} for you, sir."
                except Exception:
                    pass

        return f"I couldn't find '{app_name}', sir. I can open VS Code, Chrome, Notepad, Calculator, Paint, and more."

    async def close_app(self, app_name: str) -> str:
        """Kill a process by name. Returns spoken reply."""
        if not has_desktop_automation():
            return NO_DESKTOP_MSG

        name_l = app_name.lower()
        match  = self._detect_app(name_l)
        exe    = _APPS[match]["exe"] if match else app_name.split()[-1]
        proc_name = exe.split("\\")[-1]
        if ":" in proc_name:   # ms-settings: style — can't kill
            return f"This app can't be closed programmatically, sir."
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", proc_name],
                capture_output=True, timeout=5
            )
            return f"Closed {match.title() if match else app_name}, sir."
        except Exception as e:
            logger.error(f"Close app error: {e}")
            return "I couldn't close that, sir. You may need to close it manually."

    # ── YouTube / media ───────────────────────────────────────────────────────
    async def play_youtube(self, query: str) -> str:
        """Search YouTube and open the top video directly in browser."""
        if not query or query.lower() in ["song", "music", "a song", "me a song", "the song"]:
            query = "top trending music hits"

        logger.info(f"DesktopAutomation: playing YouTube track for '{query}'")
        url = None
        try:
            qs   = urllib.parse.urlencode({"search_query": query})
            html = await asyncio.to_thread(
                self._fetch_url,
                "https://www.youtube.com/results?" + qs
            )
            vids = re.findall(r"watch\?v=(\S{11})", html)
            if vids:
                url = f"https://www.youtube.com/watch?v={vids[0]}"
        except Exception as e:
            logger.warning(f"YouTube scrape error: {e}")

        if not url:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"

        # If running on cloud/Render, return direct link rather than trying to open server-side browser
        if not has_desktop_automation():
            return f"Playing {query} on YouTube, sir. Direct link: {url}"

        # Open in foreground on Windows
        try:
            os.startfile(url)
        except Exception:
            try:
                subprocess.Popen(f'start "" "{url}"', shell=True)
            except Exception:
                webbrowser.open(url)

        return f"Playing {query} on YouTube, sir."

    # ── Web search ────────────────────────────────────────────────────────────
    async def web_search(self, query: str) -> str:
        if not query:
            return "What should I search for, sir?"
        if not has_desktop_automation():
            return f"Searching for '{query}' on Google, sir: https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
        return f"Searching for {query} on Google, sir."

    # ── Compose / type text ───────────────────────────────────────────────────
    async def compose_in_notepad(self, content: str) -> str:
        if not content:
            return "What would you like me to write, sir?"
        if not has_desktop_automation():
            return f"Notepad automation is only available when running Jarvis locally on your Windows machine, sir. Here is your text: {content}"
        subprocess.Popen("notepad.exe", shell=True)
        await asyncio.sleep(1.8)
        if self._gui:
            await asyncio.to_thread(self._gui.write, content, 0.02)
        return "Done, sir! Text written in Notepad."

    # ── Screenshot ────────────────────────────────────────────────────────────
    async def take_screenshot(self) -> str:
        if not has_desktop_automation():
            return "Desktop screenshots are only available when running Jarvis locally on your Windows computer, sir."
        if not self._gui:
            return "Screenshot capability requires pyautogui, sir."
        try:
            folder = os.path.join(os.path.expanduser("~"), "Pictures", "Jarvis_Screenshots")
            os.makedirs(folder, exist_ok=True)
            filename = os.path.join(
                folder, f"jarvis_{time.strftime('%Y%m%d_%H%M%S')}.png"
            )
            await asyncio.to_thread(self._gui.screenshot, filename)
            return "Screenshot saved to your Pictures folder, sir."
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return "I couldn't take the screenshot, sir."

    # ── Volume control ────────────────────────────────────────────────────────
    async def control_volume(self, direction: str, percent: int = 10) -> str:
        """direction: 'up' | 'down' | 'mute' | 'unmute'"""
        if not has_desktop_automation():
            return "System volume control is only available when running Jarvis locally on your Windows machine, sir."
        if not self._gui:
            return "Volume control requires pyautogui, sir."
        try:
            gui = self._gui
            if direction == "up":
                for _ in range(max(1, percent // 2)):
                    gui.press("volumeup")
                return "Volume increased, sir."
            elif direction == "down":
                for _ in range(max(1, percent // 2)):
                    gui.press("volumedown")
                return "Volume decreased, sir."
            elif direction == "mute":
                gui.press("volumemute")
                return "Audio muted, sir."
            elif direction == "unmute":
                gui.press("volumemute")
                return "Audio unmuted, sir."
        except Exception as e:
            logger.error(f"Volume control error: {e}")
        return "I couldn't adjust the volume, sir."

    # ── Clipboard ─────────────────────────────────────────────────────────────
    async def copy_to_clipboard(self, text: str) -> str:
        if not has_desktop_automation():
            return "Clipboard access is only available on your local computer, sir."
        try:
            proc = await asyncio.create_subprocess_exec(
                "clip",
                stdin=asyncio.subprocess.PIPE,
            )
            await proc.communicate(input=text.encode("utf-16"))
            return "Copied to clipboard, sir."
        except Exception as e:
            logger.error(f"Clipboard error: {e}")
            return "I couldn't copy to clipboard, sir."

    # ── Internal helpers ──────────────────────────────────────────────────────
    def _detect_app(self, text_l: str):
        for name, data in _APPS.items():
            for kw in data["keywords"]:
                if kw in text_l:
                    return name
        # Fuzzy fallback
        for name, data in _APPS.items():
            for kw in data["keywords"]:
                if SequenceMatcher(None, text_l, kw).ratio() >= 0.6:
                    return name
        return None

    def _fetch_url(self, url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            return r.read().decode("utf-8", errors="ignore")

    async def type_text(self, text: str, interval: float = 0.02):
        if self._gui:
            await asyncio.to_thread(self._gui.write, text, interval)

    async def click_position(self, x: int, y: int):
        if self._gui:
            await asyncio.to_thread(self._gui.click, x, y)
