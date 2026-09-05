"""
Jarvis Capability & Platform Detection Engine.
Centrally manages environment-aware feature flags across Windows Desktop,
local Linux/macOS, and headless Cloud/Container environments (e.g. Render, Docker).
Ensures zero crashes from missing physical display, audio, or desktop subsystems.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("Jarvis.Capabilities")

# User-facing standard fallback messages
NO_MIC_MSG = "Local microphone is unavailable in cloud mode. Use the web interface microphone."
NO_SPEAKER_MSG = "Local speaker output is unavailable in cloud mode."
NO_DESKTOP_MSG = "Desktop application management is only available when running Jarvis locally on your Windows machine, sir."
NO_SCREEN_MSG = "Screen reading is available only when Jarvis is running on a local graphical desktop."


def is_cloud_environment() -> bool:
    """
    Determines if Jarvis is running in a headless cloud container or server.
    Detects Render, Railway, Heroku, Docker containers, or non-desktop Linux.
    """
    # Explicit platform / cloud environment flags
    if os.environ.get("RENDER") or os.environ.get("JARVIS_HEADLESS") or os.environ.get("HEADLESS_MODE"):
        return True
    if os.environ.get("DYNO") or os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("FLY_APP_NAME"):
        return True

    # Docker container indicator
    if Path("/.dockerenv").exists():
        return True

    # Headless Linux server without graphical display session
    if sys.platform != "win32" and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return True

    return False


def has_display() -> bool:
    """
    Checks whether a graphical desktop display session (X11 / Wayland / Windows) is available.
    """
    if is_cloud_environment():
        return False
    if sys.platform == "win32":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def has_audio_input() -> bool:
    """
    Checks whether physical local microphone capture hardware is available.
    In cloud containers, returns False immediately to avoid ALSA / PortAudio C-level segfaults.
    """
    if is_cloud_environment():
        return False
    if sys.platform != "win32" and not has_display():
        return False
    return True


def has_audio_output() -> bool:
    """
    Checks whether physical local speaker output hardware is available.
    In cloud containers, returns False immediately to prevent SDL/pygame ALSA crashes.
    """
    if is_cloud_environment():
        return False
    if sys.platform != "win32" and not has_display():
        return False
    return True


def has_desktop_automation() -> bool:
    """
    Checks whether Windows desktop automation (pyautogui, startfile, notepad) is available.
    """
    return sys.platform == "win32" and has_display() and not is_cloud_environment()


def get_capability_summary() -> Dict[str, Any]:
    """
    Returns a comprehensive diagnostic map of all hardware and cloud capabilities.
    """
    cloud = is_cloud_environment()
    disp = has_display()
    mic = has_audio_input()
    spk = has_audio_output()
    desk = has_desktop_automation()

    return {
        "platform": sys.platform,
        "is_cloud": cloud,
        "environment": "Headless Cloud / Docker" if cloud else "Local Desktop",
        "display_available": disp,
        "desktop_automation": desk,
        "audio_input_available": mic,
        "audio_output_available": spk,
        "web_hud_available": True,
        "websocket_available": True,
        "cloud_api_available": True,
        "memory_db_available": True,
    }
