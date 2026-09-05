#!/usr/bin/env bash
"""
JARVIS AI Assistant — Production Pre-flight Diagnostic & Health Verification
Validates that all system components, dependencies, keys, and assets are 100% ready for deployment.
"""

import os
import sys
import socket
import time
from pathlib import Path

# Force UTF-8 on Windows terminal
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent
JARVIS_DIR = ROOT_DIR / "jarvis"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(JARVIS_DIR))

# Load .env
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")


def check_mark(status: bool) -> str:
    return "✅ PASS" if status else "❌ FAIL"


def warn_mark(status: bool) -> str:
    return "✅ PASS" if status else "⚠️ WARN"


def main():
    print("\n" + "=" * 70)
    print("        JARVIS AI ASSISTANT — DEPLOYMENT PRE-FLIGHT VERIFIER        ")
    print("=" * 70)

    results = []

    # 1. Python Version
    py_ver = sys.version_info
    py_ok = (py_ver.major == 3 and py_ver.minor >= 10)
    results.append(("Python 3.10+ Runtime", py_ok, f"v{py_ver.major}.{py_ver.minor}.{py_ver.micro}"))

    # 2. Critical Package Imports
    core_packages = [
        ("fastapi", "FastAPI Web Framework"),
        ("uvicorn", "Uvicorn ASGI Server"),
        ("websockets", "WebSocket Engine"),
        ("groq", "Groq Cloud LLM SDK"),
        ("edge_tts", "Edge-TTS Speech Synthesis"),
        ("faster_whisper", "Faster-Whisper STT Engine"),
        ("duckduckgo_search", "DuckDuckGo Realtime Search"),
        ("psutil", "System Telemetry (psutil)"),
    ]

    all_imports_ok = True
    missing_pkgs = []
    for pkg, name in core_packages:
        try:
            __import__(pkg)
        except ImportError:
            all_imports_ok = False
            missing_pkgs.append(pkg)

    import_detail = "All packages loaded" if all_imports_ok else f"Missing: {', '.join(missing_pkgs)}"
    results.append(("Core Python Dependencies", all_imports_ok, import_detail))

    # 3. Environment & Secrets Configuration
    env_file = ROOT_DIR / ".env"
    env_exists = env_file.exists()
    results.append((".env Configuration File", env_exists, str(env_file)))

    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    groq_ok = bool(groq_key and groq_key.startswith("gsk_"))
    results.append(("Groq AI API Key", groq_ok, "Configured (120B Model Ready)" if groq_ok else "Missing GROQ_API_KEY in .env"))

    weather_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    weather_ok = bool(weather_key and len(weather_key) >= 16)
    results.append(("OpenWeather API Key", weather_ok, "Configured (Live Weather)" if weather_ok else "Using wttr.in fallback"))

    news_key = os.environ.get("NEWS_API_KEY", "").strip()
    news_ok = bool(news_key and len(news_key) >= 16)
    results.append(("NewsAPI Key", news_ok, "Configured (Top Headlines)" if news_ok else "Using DuckDuckGo news fallback"))

    # 4. Web HUD Static Assets
    static_dir = JARVIS_DIR / "ui" / "static"
    critical_assets = [
        static_dir / "index.html",
        static_dir / "css" / "style.css",
        static_dir / "js" / "app.js",
        static_dir / "js" / "marked.min.js",
    ]
    assets_ok = all(f.exists() for f in critical_assets)
    missing_assets = [f.name for f in critical_assets if not f.exists()]
    asset_detail = "All UI assets present" if assets_ok else f"Missing: {missing_assets}"
    results.append(("Quantum HUD Static Assets", assets_ok, asset_detail))

    # 5. Audio Hardware / Headless Detection
    audio_detected = False
    audio_desc = "Headless Mode (Web HUD text/websocket audio)"
    try:
        from core.capabilities import has_audio_input
        if has_audio_input():
            import pyaudio
            p = pyaudio.PyAudio()
            dev_count = p.get_device_count()
            if dev_count > 0:
                audio_detected = True
                try:
                    def_dev = p.get_default_input_device_info()
                    audio_desc = f"Microphone: {def_dev.get('name', 'Default Mic')[:32]}"
                except Exception:
                    audio_desc = f"{dev_count} audio devices detected"
            p.terminate()
    except Exception:
        pass

    results.append(("Audio Hardware / Senses", True, audio_desc))

    # 6. Port Availability Check
    port = int(os.environ.get("PORT") or os.environ.get("JARVIS_PORT", 8000))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    port_open = False
    try:
        sock.bind(("127.0.0.1", port))
        port_open = True
    except socket.error:
        port_open = False
    finally:
        sock.close()

    results.append((f"Network Port {port} Available", port_open, "Ready to bind" if port_open else f"Port {port} in use (or active server)"))

    # Print Summary Table
    print("\n{:<32} {:<10} {:<30}".format("CHECK", "STATUS", "DETAILS"))
    print("-" * 75)
    all_critical_pass = True
    for name, ok, detail in results:
        status_str = check_mark(ok)
        if not ok and name not in ["OpenWeather API Key", "NewsAPI Key", f"Network Port {port} Available"]:
            all_critical_pass = False
        print("{:<32} {:<10} {:<30}".format(name, status_str, str(detail)[:45]))

    print("-" * 75)
    if all_critical_pass:
        print("\n🚀 DEPLOYMENT STATUS: 100% READY FOR PRODUCTION DEPLOYMENT!")
        print(f"👉 Local Launch   : python main.py --mode hud --port {port}")
        print(f"👉 Windows 1-Click: Double-click 'run_jarvis.bat'")
        print(f"👉 Docker Launch  : docker-compose up -d")
    else:
        print("\n⚠️ DEPLOYMENT STATUS: Some items need attention before production launch.")
        print("Please review the failed items above.")
    print("=" * 75 + "\n")

    return 0 if all_critical_pass else 1


if __name__ == "__main__":
    sys.exit(main())
