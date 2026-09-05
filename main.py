"""
Jarvis AI Assistant — Unified Entry Point
Supports Live Web HUD Mode (with 60FPS Reactive Visualizer),
Headless Voice Mode, and Interactive Terminal REPL Mode.
"""

import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import argparse
import asyncio
import io
import logging
import sys
import webbrowser
from pathlib import Path

# ── Force UTF-8 on Windows terminal ───────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Load .env ─────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
JARVIS_DIR = ROOT_DIR / "jarvis"
ENV_PATH = ROOT_DIR / ".env"

if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

# Add jarvis to sys.path so its internal modules resolve
sys.path.insert(0, str(JARVIS_DIR))

# ── Core & Agent Imports ──────────────────────────────────────────────────────
from core.event_bus import EventBus
from core.orchestrator import Orchestrator
from core.skill_registry import SkillRegistry
from core.capabilities import (
    is_cloud_environment,
    has_display,
    has_audio_input,
    has_audio_output,
    has_desktop_automation,
    get_capability_summary,
    NO_MIC_MSG,
    NO_SPEAKER_MSG,
)
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from models.router import ModelRouter
from perception.audio.pipeline import AudioPipeline
from perception.audio.tts_edge import TTSEdge
from perception.vision.screen_reader import ScreenReader
from plugins.manager import PluginManager
from ui.web_server import JarvisWebServer

from agents.conversation_agent import ConversationAgent
from agents.desktop_agent import DesktopAgent
from agents.system_agent import SystemAgent
from agents.weather_agent import WeatherAgent
from agents.news_agent import NewsAgent
from agents.reminder_agent import ReminderAgent

logger = logging.getLogger("Jarvis")


class SpeakHandler:
    """Subscribes to Action.Speak on the event bus, prints, plays voice, and coordinates mic."""

    def __init__(self, tts: TTSEdge, long_term: LongTermMemory, silent: bool = False, reply_event: asyncio.Event = None):
        self.tts = tts
        self.long_term = long_term
        self.silent = silent
        self.reply_event = reply_event
        self.audio_pipeline = None

    async def handle(self, payload: dict):
        text = payload.get("text", "").strip()
        voice_text = payload.get("voice_text", "").strip() or text
        if not text:
            if self.audio_pipeline:
                self.audio_pipeline.unmute()
            if self.reply_event:
                self.reply_event.set()
            return

        print(f"\n[Jarvis]: {text}\n")

        # Persist to long-term memory
        try:
            self.long_term.store("assistant", text)
        except Exception:
            pass

        # Switch mic pipeline to SPEAKING to prevent hearing itself
        if self.audio_pipeline:
            self.audio_pipeline.set_state("SPEAKING")

        if not self.silent:
            try:
                await self.tts.speak(voice_text)
            except Exception as e:
                logger.error(f"TTS playback failed: {e}")

        # Short pause for room echo to decay, then immediately re-arm continuous mic
        if self.audio_pipeline:
            await asyncio.sleep(0.35)
            self.audio_pipeline.unmute()

        if self.reply_event:
            self.reply_event.set()


def print_banner(mode: str, hud_url: str = ""):
    caps = get_capability_summary()
    env_label = caps["environment"]
    mic_label = "Local Microphone (PyAudio Continuous VAD)" if caps["audio_input_available"] else "Web HUD Client Microphone (Cloud Safe)"
    spk_label = "Local Speakers (Edge-TTS / PyGame)" if caps["audio_output_available"] else "Web HUD Audio / Reactive Visualizer"
    disp_label = "Graphical Desktop Active" if caps["display_available"] else "Headless Server (Web HUD & WebSocket Only)"

    banner = f"""
==================================================================
                    JARVIS AI ASSISTANT v2.0                      
        Quantum Live HUD • Continuous Voice • Dual Input          
==================================================================
  * Active Mode : {mode.upper()}
  * Environment : {env_label}
  * Web HUD     : {hud_url if hud_url else "Disabled (Terminal Only)"}
  * Display     : {disp_label}
  * Audio Input : {mic_label}
  * Audio Output: {spk_label}
  * Core Engine : EventBus + Multi-Agent Orchestrator + Groq LLM
  * Agents      : Conversation, Desktop, System, Weather, News, Reminder
------------------------------------------------------------------
"""
    print(banner)


async def text_repl_loop(event_bus: EventBus, reply_event: asyncio.Event):
    """Interactive text REPL loop for testing & typing commands in terminal."""
    print("Type a command or question below (type 'exit' or 'quit' to stop):\n")
    loop = asyncio.get_running_loop()

    while True:
        try:
            user_input = await loop.run_in_executor(None, input, "Sir > ")
            user_input = user_input.strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Powering down. Goodbye sir.")
                break

            reply_event.clear()
            await event_bus.publish("Input.Text", {"text": user_input, "source": "terminal"})

            try:
                await asyncio.wait_for(reply_event.wait(), timeout=15.0)
            except asyncio.TimeoutError:
                pass

        except (KeyboardInterrupt, EOFError):
            break


async def run_jarvis(
    mode: str = "hud",
    silent: bool = False,
    verbose: bool = False,
    open_browser: bool = True,
    host: str = "127.0.0.1",
    port: int = 8000,
):
    # Support dynamic cloud hosting environment variables (e.g. Render, Railway, Heroku)
    env_port = os.environ.get("PORT") or os.environ.get("JARVIS_PORT")
    if env_port and env_port.isdigit():
        port = int(env_port)

    env_host = os.environ.get("JARVIS_HOST") or os.environ.get("HOST")
    if env_host:
        host = env_host

    log_level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    hud_url = f"http://{host}:{port}" if mode in ["hud", "web"] else ""
    print_banner(mode, hud_url)

    # 1. Infrastructure
    reply_event = asyncio.Event()
    event_bus = EventBus()
    short_term = ShortTermMemory(max_history=20)
    long_term = LongTermMemory()
    model_router = ModelRouter()
    skill_reg = SkillRegistry()
    orchestrator = Orchestrator(event_bus, model_router)

    # 2. Plugins
    plugin_dir = str(JARVIS_DIR / "plugins")
    plugin_manager = PluginManager(plugins_dir=plugin_dir)
    plugin_manager.discover_and_load()

    # 3. Speech Output
    tts = TTSEdge(voice="en-US-AriaNeural")
    speak_handler = SpeakHandler(tts=tts, long_term=long_term, silent=silent, reply_event=reply_event)
    event_bus.subscribe("Action.Speak", speak_handler.handle)

    # 4. Worker Agents
    desktop_agent = DesktopAgent(event_bus=event_bus, model_router=model_router)
    system_agent = SystemAgent(event_bus=event_bus)
    conv_agent = ConversationAgent(
        event_bus=event_bus,
        model_router=model_router,
        short_term_memory=short_term,
        skill_registry=skill_reg,
    )
    weather_agent = WeatherAgent(event_bus=event_bus)
    news_agent = NewsAgent(event_bus=event_bus)
    reminder_agent = ReminderAgent(event_bus=event_bus)

    # 5. User Input Logging Hook
    async def _log_input(payload: dict):
        text = payload.get("text", "").strip()
        if text:
            short_term.add_turn("user", text)
            long_term.store("user", text)

    event_bus.subscribe("Input.Text", _log_input)

    # 6. Start Core Engine
    bus_task = event_bus.start()
    orch_task = orchestrator.start()
    reminder_task = reminder_agent.start()

    # 7. Start Web HUD Server if in HUD/Web mode (binds instantly)
    web_server = None
    web_task = None
    if mode in ["hud", "web"]:
        web_server = JarvisWebServer(event_bus, audio_pipeline=None, tts=tts, host=host, port=port)
        web_task = asyncio.create_task(web_server.run_server())

        if open_browser and has_display() and not is_cloud_environment():
            async def _open_browser():
                await asyncio.sleep(0.8)
                # When bound to 0.0.0.0, open 127.0.0.1 in local browser
                browser_target = f"http://127.0.0.1:{port}" if host in ["0.0.0.0", "::"] else hud_url
                webbrowser.open(browser_target)
            asyncio.create_task(_open_browser())

    # 8. Start Voice Pipeline (Continuous listening by default in hud and voice modes)
    audio_pipeline = None
    if mode in ["hud", "web", "voice", "dual"]:
        try:
            audio_pipeline = AudioPipeline(event_bus, tts_engine=tts)
            speak_handler.audio_pipeline = audio_pipeline
            if web_server:
                web_server.audio_pipeline = audio_pipeline
                web_server._subscribe_events()

            if has_audio_input():
                audio_pipeline.start()
                logger.info("Continuous voice pipeline online.")
            else:
                logger.info(f"Cloud mode active: {NO_MIC_MSG}")
        except Exception as e:
            logger.error(f"Could not initialize audio pipeline: {e}")
            print(f"[Warning] Microphone pipeline unavailable: {e}")

    # 9. Startup Greeting (Spoken after mic is armed and visualizer is active)
    greeting_text = (
        "Hello sir! Jarvis is online and fully operational. How may I assist you today?"
    )
    if not silent:
        try:
            await tts.speak(greeting_text)
        except Exception:
            pass
    print(f"[Jarvis]: {greeting_text}\n")

    # 10. Keep-alive execution loop
    try:
        if mode == "text":
            await text_repl_loop(event_bus, reply_event)
        elif mode == "dual":
            repl_task = asyncio.create_task(text_repl_loop(event_bus, reply_event))
            await repl_task
        elif web_task:
            await web_task
        else:
            print("Listening for voice commands. Press Ctrl+C to terminate.")
            while True:
                await asyncio.sleep(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        logger.info("Shutting down Jarvis...")
        if web_server:
            web_server.stop()
        reminder_agent.stop()
        orchestrator.stop()
        event_bus.stop()
        if audio_pipeline:
            audio_pipeline.stop()
        bus_task.cancel()
        orch_task.cancel()
        reminder_task.cancel()
        if web_task:
            web_task.cancel()
        logger.info("Jarvis offline. Goodbye.")


def parse_arguments():
    default_host = os.environ.get("JARVIS_HOST") or os.environ.get("HOST", "127.0.0.1")
    default_port = int(os.environ.get("PORT") or os.environ.get("JARVIS_PORT", 8000))

    parser = argparse.ArgumentParser(description="Jarvis AI Assistant Entry Point")
    parser.add_argument(
        "-m",
        "--mode",
        choices=["hud", "web", "voice", "text", "dual"],
        default="hud",
        help="Execution mode: hud (Web UI + continuous voice), voice (CLI voice only), text (CLI text only)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=default_host,
        help=f"Host interface to bind the Live Web HUD (default: {default_host})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
        help=f"Port to serve the Live Web HUD (default: {default_port})",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the browser when launching HUD",
    )
    parser.add_argument(
        "-t",
        "--text",
        action="store_true",
        help="Shortcut to run in interactive terminal text mode",
    )
    parser.add_argument(
        "-s",
        "--silent",
        action="store_true",
        help="Suppress TTS voice audio playback",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed debug/info logs in console",
    )
    args = parser.parse_args()

    mode = args.mode
    if args.text:
        mode = "text"

    should_open_browser = (not args.no_browser) and has_display() and not is_cloud_environment()
    return mode, args.silent, args.verbose, should_open_browser, args.host, args.port


def main():
    mode, silent, verbose, open_browser, host, port = parse_arguments()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(
            run_jarvis(
                mode=mode,
                silent=silent,
                verbose=verbose,
                open_browser=open_browser,
                host=host,
                port=port,
            )
        )
    except KeyboardInterrupt:
        print("\nSession ended by user.")


if __name__ == "__main__":
    main()
