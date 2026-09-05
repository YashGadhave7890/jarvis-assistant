"""
Jarvis Web HUD & Real-Time WebSocket Server.
Bridges the Python EventBus and AudioPipeline to a dynamic, reactive browser interface.
"""

import asyncio
import json
import logging
import os
import psutil
import time
from pathlib import Path
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from core.event_bus import EventBus

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


class JarvisWebServer:
    def __init__(self, event_bus: EventBus, audio_pipeline=None, tts=None, host: str = "127.0.0.1", port: int = 8000):
        self.bus = event_bus
        self.audio_pipeline = audio_pipeline
        self.tts = tts
        self.host = host
        self.port = port
        self.app = FastAPI(title="Jarvis HUD AI Assistant", version="2.5.0")
        self.active_connections: Set[WebSocket] = set()
        self.loop = None
        self.start_time = time.time()
        self._server = None
        self._setup_routes()
        self._subscribe_events()

    def _setup_routes(self):
        # Enable CORS for local network, mobile devices, and remote proxies
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Mount static assets
        if not STATIC_DIR.exists():
            STATIC_DIR.mkdir(parents=True, exist_ok=True)

        self.app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @self.app.get("/")
        async def get_index():
            index_file = STATIC_DIR / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return {"status": "Jarvis HUD ready. Loading static interface..."}

        @self.app.get("/health")
        async def health_check():
            """Production healthcheck endpoint for Docker, Kubernetes, and Cloud monitors."""
            mem = psutil.Process().memory_info()
            try:
                from core.capabilities import get_capability_summary, has_audio_input
                caps = get_capability_summary()
                has_hw_mic = has_audio_input()
            except Exception:
                caps = {}
                has_hw_mic = False

            audio_hw_running = bool(self.audio_pipeline and getattr(self.audio_pipeline, "is_running", False))
            audio_healthy = audio_hw_running if has_hw_mic else True
            audio_mode = (
                "hardware_continuous_vad"
                if (has_hw_mic and audio_hw_running)
                else ("client_web_speech" if not has_hw_mic else "hardware_idle")
            )

            return {
                "status": "healthy",
                "service": "Jarvis AI Assistant",
                "version": "2.5.0",
                "uptime_seconds": round(time.time() - self.start_time, 2),
                "active_connections": len(self.active_connections),
                "audio_pipeline_active": audio_healthy,
                "audio_hardware_running": audio_hw_running,
                "audio_mode": audio_mode,
                "memory_mb": round(mem.rss / (1024 * 1024), 2),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
                "environment": caps.get("environment", "Unknown"),
                "capabilities": caps,
            }

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.add(websocket)
            logger.info(f"WebSocket client connected. Active: {len(self.active_connections)}")

            # Send initial state
            mic_state = self.audio_pipeline.state if self.audio_pipeline else "LISTENING"
            is_muted = self.audio_pipeline.is_muted if self.audio_pipeline else False
            threshold = getattr(self.audio_pipeline, "silence_threshold", 0.0025)
            listening_mode = getattr(self.audio_pipeline, "listening_mode", "continuous")
            voice_gender = "female" if (self.tts and "Aria" in getattr(self.tts, "voice", "")) else "male"

            await websocket.send_json({
                "type": "init",
                "state": mic_state,
                "is_muted": is_muted,
                "threshold": threshold,
                "listening_mode": listening_mode,
                "voice_gender": voice_gender,
                "uptime": int(time.time() - self.start_time),
                "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
            })

            try:
                while True:
                    data = await websocket.receive_text()
                    try:
                        msg = json.loads(data)
                        await self._handle_client_message(msg, websocket)
                    except json.JSONDecodeError:
                        pass
            except (WebSocketDisconnect, asyncio.CancelledError):
                self.active_connections.discard(websocket)
                logger.info("WebSocket client disconnected.")
            except Exception as e:
                self.active_connections.discard(websocket)
                logger.debug(f"WebSocket connection closed: {e}")

    async def _handle_client_message(self, msg: dict, websocket: WebSocket):
        action = msg.get("action")

        if action == "send_text":
            text = msg.get("text", "").strip()
            if text:
                logger.info(f"[HUD] User typed: '{text}'")
                await self.bus.publish("Input.Text", {"text": text, "source": "web_input"})

        elif action == "toggle_mic":
            if self.audio_pipeline:
                mute_req = msg.get("mute")
                if mute_req is True:
                    self.audio_pipeline.mute()
                elif mute_req is False:
                    self.audio_pipeline.unmute()
                else:
                    if self.audio_pipeline.is_muted:
                        self.audio_pipeline.unmute()
                    else:
                        self.audio_pipeline.mute()
                await self.broadcast({
                    "type": "mic_toggled",
                    "is_muted": self.audio_pipeline.is_muted,
                    "state": self.audio_pipeline.state,
                })

        elif action == "set_threshold":
            val = float(msg.get("value", 0.0025))
            if self.audio_pipeline:
                self.audio_pipeline.silence_threshold = max(0.0005, min(val, 0.02))
                logger.info(f"[HUD] Mic threshold set to: {self.audio_pipeline.silence_threshold:.5f}")

        elif action == "set_voice":
            gender = msg.get("gender", "male")
            if self.tts:
                self.tts.set_voice(gender)
                logger.info(f"[HUD] Voice switched to: {gender} ({self.tts.voice})")
            await self.broadcast({
                "type": "voice_switched",
                "gender": gender,
                "voice": self.tts.voice if self.tts else gender,
            })

        elif action == "set_listening_mode":
            mode = msg.get("mode", "continuous").lower().strip()
            if self.audio_pipeline:
                self.audio_pipeline.set_listening_mode(mode)
            await self.broadcast({
                "type": "listening_mode_changed",
                "mode": mode,
            })

        elif action == "set_ptt":
            active = bool(msg.get("active", False))
            if self.audio_pipeline:
                self.audio_pipeline.set_ptt(active)

        elif action == "set_speech_rate":
            rate = int(msg.get("rate", 0))
            if self.tts:
                self.tts.set_rate(rate)
            await self.broadcast({
                "type": "speech_rate_changed",
                "rate": rate,
            })

        elif action == "stop_speech":
            if self.tts:
                self.tts.stop()
            await self.bus.publish("Audio.Interrupted", {})
            await self.broadcast({"type": "interrupted"})

        elif action == "get_memory":
            memories = []
            try:
                from memory.long_term import LongTermMemory
                ltm = LongTermMemory()
                rows = ltm.fetch_recent(limit=25)
                memories = [{"time": str(r[0]), "role": str(r[1]), "content": str(r[2])} for r in rows]
            except Exception as e:
                logger.error(f"Error fetching memory: {e}")

            try:
                from core.capabilities import has_desktop_automation, has_display, has_audio_input
                desk_status = "Ready" if has_desktop_automation() else "Local PC Only"
                vision_status = "Active" if has_display() else "Headless Cloud"
                audio_status = "Live (Hardware)" if has_audio_input() else "Web Mic Ready"
            except Exception:
                desk_status, vision_status, audio_status = "Ready", "Active", "Live"

            tools = [
                {"name": "YouTube & Media", "icon": "fa-youtube", "status": "Ready", "desc": "Audio & video playback"},
                {"name": "Desktop Apps", "icon": "fa-laptop-code", "status": desk_status, "desc": "Launch & automate applications"},
                {"name": "Screen Vision", "icon": "fa-eye", "status": vision_status, "desc": "Snapshot & window perception"},
                {"name": "Weather Service", "icon": "fa-cloud-sun", "status": "Ready", "desc": "Live atmospheric conditions"},
                {"name": "Web Search", "icon": "fa-globe", "status": "Ready", "desc": "Real-time web knowledge retrieval"},
                {"name": "Audio Pipeline", "icon": "fa-microphone-lines", "status": audio_status, "desc": "Adaptive VAD & barge-in"},
            ]
            await websocket.send_json({
                "type": "memory_data",
                "memories": memories,
                "tools": tools,
            })

        elif action == "request_telemetry":
            await self._broadcast_telemetry()

    async def broadcast(self, payload: dict):
        """Broadcasts a JSON message to all active WebSocket clients."""
        if not self.active_connections:
            return
        dead = set()
        msg_str = json.dumps(payload)
        for ws in list(self.active_connections):
            try:
                await ws.send_text(msg_str)
            except Exception:
                dead.add(ws)
        self.active_connections.difference_update(dead)

    def _broadcast_from_thread(self, payload: dict):
        if self.loop and self.loop.is_running() and self.active_connections:
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), self.loop)

    def _hook_audio_pipeline(self):
        if not self.audio_pipeline:
            return
        original_on_energy = self.audio_pipeline.on_energy
        def wrapped_energy(normalized, raw):
            if original_on_energy:
                original_on_energy(normalized, raw)
            self._broadcast_from_thread({
                "type": "energy",
                "normalized": round(normalized, 3),
                "raw": round(raw, 5),
            })
        self.audio_pipeline.on_energy = wrapped_energy

        original_on_state = self.audio_pipeline.on_state
        def wrapped_state(state):
            if original_on_state:
                original_on_state(state)
            self._broadcast_from_thread({
                "type": "state",
                "state": state,
            })
        self.audio_pipeline.on_state = wrapped_state

    def _subscribe_events(self):
        self._hook_audio_pipeline()

        if getattr(self, "_bus_subscribed", False):
            return
        self._bus_subscribed = True

        # Event bus subscriptions
        async def on_user_input(p: dict):
            await self.broadcast({
                "type": "user_input",
                "text": p.get("text", ""),
                "source": p.get("source", "voice"),
            })

        async def on_thinking(p: dict):
            await self.broadcast({
                "type": "thinking",
                "text": p.get("text", ""),
            })

        async def on_routed(p: dict):
            await self.broadcast({
                "type": "routed",
                "agent": p.get("agent", ""),
                "intent": p.get("intent", ""),
                "confidence": round(p.get("confidence", 1.0), 2),
                "text": p.get("text", ""),
            })

        async def on_speak(p: dict):
            await self.broadcast({
                "type": "response",
                "text": p.get("text", ""),
                "voice_text": p.get("voice_text", ""),
            })

        async def on_screenshot(p: dict):
            await self.broadcast({
                "type": "screenshot",
                "url": p.get("web_url", ""),
                "active_window": p.get("active_window", "Desktop"),
                "open_windows": p.get("open_windows", []),
            })

        async def on_interrupted(p: dict):
            await self.broadcast({
                "type": "interrupted",
            })

        self.bus.subscribe("Input.Text", on_user_input)
        self.bus.subscribe("Jarvis.Thinking", on_thinking)
        self.bus.subscribe("Jarvis.Routed", on_routed)
        self.bus.subscribe("Action.Speak", on_speak)
        self.bus.subscribe("UI.Screenshot", on_screenshot)
        self.bus.subscribe("Audio.Interrupted", on_interrupted)

    async def _telemetry_loop(self):
        while True:
            try:
                await asyncio.sleep(3.0)
                if self.active_connections:
                    await self._broadcast_telemetry()
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(3.0)

    async def _broadcast_telemetry(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        has_local_mic = bool(self.audio_pipeline and getattr(self.audio_pipeline, "stream", None) and getattr(self.audio_pipeline, "audio", None))
        mic_name = "Web Microphone (Client-side)"
        if has_local_mic:
            mic_name = "Default Microphone"
            try:
                info = self.audio_pipeline.audio.get_device_info_by_index(self.audio_pipeline._device_index)
                mic_name = info.get("name", mic_name)
            except Exception:
                pass

        await self.broadcast({
            "type": "telemetry",
            "cpu": cpu,
            "ram": ram,
            "mic_name": mic_name,
            "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
            "state": self.audio_pipeline.state if self.audio_pipeline else "IDLE",
            "is_muted": self.audio_pipeline.is_muted if self.audio_pipeline else False,
            "uptime": int(time.time() - self.start_time),
        })

    async def run_server(self):
        self.loop = asyncio.get_running_loop()
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        asyncio.create_task(self._telemetry_loop())
        logger.info(f"Jarvis Web HUD live at http://{self.host}:{self.port}")
        await self._server.serve()

    def stop(self):
        if self._server:
            self._server.should_exit = True
