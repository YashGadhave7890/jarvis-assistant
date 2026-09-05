"""
Advanced Desktop Agent — routes intent payloads from the Orchestrator to
the correct DesktopAutomation method, then speaks the result.
"""

import asyncio
import logging
import re
from agents.base_agent import BaseAgent
from action.desktop import DesktopAutomation
from core.event_bus import EventBus
from perception.vision.screen_reader import ScreenReader

logger = logging.getLogger(__name__)


class DesktopAgent(BaseAgent):
    """
    Handles: open_app, close_app, play_media, web_search, compose_text,
             screenshot, analyze_screen, stop_speech, volume_control, clipboard.
    """

    def __init__(self, event_bus: EventBus, model_router=None):
        super().__init__(name="Desktop", event_bus=event_bus)
        self.automation   = DesktopAutomation(event_bus)
        self.model_router = model_router
        self.screen_reader = ScreenReader()

    async def execute(self, payload: dict):
        intent   = payload.get("intent",   "open_app")
        entities = payload.get("entities", {})
        text     = payload.get("text",     "")
        t        = text.lower()
        logger.info(f"DesktopAgent: intent='{intent}' entities={entities}")

        reply = await self._dispatch(intent, entities, t, text)
        await self.emit_action("Action.Speak", {"text": reply})

    async def _dispatch(self, intent: str, entities: dict, t: str, text: str) -> str:

        # ── Emotional support / Mood-based media action ───────────────────────
        if intent == "mood_action":
            query = entities.get("query", "uplifting comforting songs to cheer up")
            intro = entities.get(
                "spoken_intro",
                "I'm here with you, sir. Let me play some soothing, comforting music to help you feel better."
            )
            # Immediately trigger YouTube playback on laptop
            await self.automation.play_youtube(query)
            return intro

        # ── Play media / YouTube ──────────────────────────────────────────────
        if intent == "play_media":
            query = entities.get("query", "").strip()
            intro = entities.get("spoken_intro", "")
            if not query:
                # Extract manually from raw text
                query = re.sub(
                    r"\b(play|song|music|youtube|video|listen|on|put|on)\b", "", t
                ).strip()
            if not query:
                query = "top trending music hits"

            # Open media
            play_res = await self.automation.play_youtube(query)
            return intro or play_res

        # ── Web search ────────────────────────────────────────────────────────
        if intent == "web_search":
            query = entities.get("query", "").strip()
            if not query:
                query = re.sub(
                    r"\b(search|find|google|look|up|browse|for|news)\b", "", t
                ).strip()
            return await self.automation.web_search(query)

        # ── Compose / write text ──────────────────────────────────────────────
        if intent == "compose_text":
            content = entities.get("content", "").strip()
            if not content:
                content = re.sub(
                    r"\b(write|type|note|create|make|a|letter|in|notepad|draft|compose)\b", "", t
                ).strip()
            # Let AI expand/refine if the request is abstract
            if self.model_router and content and len(content.split()) > 3:
                try:
                    ai_content = await self.model_router.generate_response(
                        f"Write the following in full, no preamble, no markdown: {content}"
                    )
                    if ai_content and len(ai_content) > 20:
                        content = ai_content.strip()
                except Exception:
                    pass
            return await self.automation.compose_in_notepad(content)

        # ── Open app ─────────────────────────────────────────────────────────
        if intent == "open_app":
            app_name = entities.get("app_name", "").strip()
            if not app_name:
                app_name = t
            app_name = re.sub(r"\b(and all that|please|for me|and that|app|application)\b", "", app_name, flags=re.IGNORECASE).strip()
            return await self.automation.launch_app(app_name)

        # ── Close app ────────────────────────────────────────────────────────
        if intent == "close_app":
            app_name = entities.get("app_name", t).strip()
            return await self.automation.close_app(app_name)

        # ── Screenshot ───────────────────────────────────────────────────────
        if intent == "screenshot":
            cap = await self.screen_reader.capture_screen()
            if cap.get("success"):
                await self.bus.publish("UI.Screenshot", cap)
                return f"Screenshot captured, sir. Focused on {cap.get('active_window', 'your screen')}."
            return await self.automation.take_screenshot()

        # ── Multimodal Screen Vision / Analysis ──────────────────────────────
        if intent == "analyze_screen":
            cap = await self.screen_reader.capture_screen()
            if cap.get("success"):
                await self.bus.publish("UI.Screenshot", cap)
                active_win = cap.get("active_window", "Desktop")
                open_wins = ", ".join(cap.get("open_windows", [])) or "None"

                if self.model_router:
                    prompt = (
                        f"You are Jarvis. The user asked: '{text}'. "
                        f"Current active window on user's screen: '{active_win}'. "
                        f"Other open desktop windows: {open_wins}. "
                        "Provide a concise, direct, helpful 1-2 sentence response explaining what they are looking at or working on."
                    )
                    try:
                        ai_reply = await self.model_router.generate_response(prompt)
                        if ai_reply and len(ai_reply.strip()) > 5:
                            return ai_reply.strip()
                    except Exception as e:
                        logger.error(f"Screen vision AI error: {e}")

                return f"You are currently viewing {active_win}. Open windows include {open_wins}."
            return "I was unable to capture your screen, sir."

        # ── Immediate stop / barge-in cancellation ───────────────────────────
        if intent == "stop_speech":
            await self.bus.publish("Audio.Interrupted", {})
            return "Speech paused, sir."

        # ── Volume control ────────────────────────────────────────────────────
        if intent == "volume_control":
            direction = entities.get("direction", "up")
            percent   = int(entities.get("percent", 10))
            return await self.automation.control_volume(direction, percent)

        # ── Clipboard ────────────────────────────────────────────────────────
        if intent == "clipboard":
            content = entities.get("content", text)
            return await self.automation.copy_to_clipboard(content)

        # ── Fallback: try to launch by app name in raw text ───────────────────
        if any(k in t for k in ["open", "launch", "start", "run"]):
            return await self.automation.launch_app(t)

        return "I'm not sure how to do that, sir. Could you rephrase?"
