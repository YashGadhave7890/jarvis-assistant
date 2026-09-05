"""
Advanced Conversation Agent — context-aware, multi-turn, memory-backed.
Uses ShortTermMemory to maintain conversation history and pass it to Groq
for truly context-aware responses.
"""

import logging
import random
import datetime
import re
from agents.base_agent import BaseAgent
from core.event_bus import EventBus
from core.skill_registry import SkillRegistry
from memory.short_term import ShortTermMemory

logger = logging.getLogger(__name__)


# ── Canned response pools ──────────────────────────────────────────────────────
_GREETINGS = [
    "Hello sir! It's great to hear from you. How can I assist?",
    "Good day, sir! I'm fully operational and at your service.",
    "Hi there! All systems running perfectly. What shall we do today?",
    "Hey sir! Ready and listening. How may I help you?",
]

_THANKS = [
    "You're most welcome, sir! Always a pleasure to assist.",
    "My pleasure, sir! Is there anything else you need?",
    "Glad I could help, sir! What's next?",
    "Happy to serve, sir! Just say the word.",
]

_FAREWELLS = [
    "Goodbye sir! Have a wonderful day. I'll be here when you need me.",
    "Take care, sir! Powering down listening mode.",
    "Farewell sir! Always here if you need anything.",
]

_STATUS_MSGS = [
    "I'm running at full capacity, sir! All systems green. How can I help?",
    "Performing excellently, sir! Every module is operational. What do you need?",
    "In top shape, sir! Ready for any task you throw at me.",
]


class ConversationAgent(BaseAgent):
    """
    Handles: greetings, farewells, thanks, status, help, and open-ended AI Q&A.
    Maintains multi-turn context via ShortTermMemory for coherent conversation.
    """

    MAX_RESPONSE_CHARS = 500   # chars before voice truncation
    HISTORY_TURNS = 6          # how many past turns to include in the prompt

    def __init__(
        self,
        event_bus: EventBus,
        model_router=None,
        short_term_memory: ShortTermMemory = None,
        skill_registry: SkillRegistry = None,
    ):
        super().__init__(name="Conversation", event_bus=event_bus)
        self.model_router  = model_router
        self.memory        = short_term_memory or ShortTermMemory(max_history=20)
        self.skill_registry = skill_registry or SkillRegistry()

    async def execute(self, payload: dict):
        text   = payload.get("text", "").strip()
        intent = payload.get("intent", "ask_ai")
        t      = text.lower()
        logger.info(f"ConversationAgent: intent='{intent}' text='{text}'")

        has_llm = bool(self.model_router and getattr(self.model_router, "groq_client", None))

        # ── Canned handlers (ONLY when offline / no LLM configured) ────────────
        if not has_llm:
            if intent == "greeting" or any(
                w in t for w in ["hello", "hi jarvis", "hey jarvis", "good morning",
                                 "good evening", "good afternoon"]
            ):
                reply = random.choice(_GREETINGS)
                self.memory.add_turn("assistant", reply)
                await self.emit_action("Action.Speak", {"text": reply})
                return

            if intent == "farewell" or any(
                w in t for w in ["goodbye", "bye", "see you", "that's all for now"]
            ):
                reply = random.choice(_FAREWELLS)
                self.memory.add_turn("assistant", reply)
                await self.emit_action("Action.Speak", {"text": reply})
                return

            if any(w in t for w in ["thank", "thanks", "thank you", "great job", "well done", "awesome"]):
                reply = random.choice(_THANKS)
                self.memory.add_turn("assistant", reply)
                await self.emit_action("Action.Speak", {"text": reply})
                return

            if any(w in t for w in ["how are you", "how are u", "are you okay", "you okay", "what's up"]):
                reply = random.choice(_STATUS_MSGS)
                self.memory.add_turn("assistant", reply)
                await self.emit_action("Action.Speak", {"text": reply})
                return

            if any(w in t for w in ["help", "what can you do", "your skills", "commands", "capabilities"]):
                reply = self._build_help_text()
                self.memory.add_turn("assistant", reply)
                await self.emit_action("Action.Speak", {"text": reply})
                return

            if any(w in t for w in ["what time is it", "current time", "tell me the time"]):
                now   = datetime.datetime.now().strftime("%I:%M %p")
                reply = f"The current time is {now}, sir."
                self.memory.add_turn("assistant", reply)
                await self.emit_action("Action.Speak", {"text": reply})
                return

            if any(w in t for w in ["what day is it", "what's the date", "today's date", "what date"]):
                today = datetime.datetime.now().strftime("%A, %B %d %Y")
                reply = f"Today is {today}, sir."
                self.memory.add_turn("assistant", reply)
                await self.emit_action("Action.Speak", {"text": reply})
                return

        # ── Proactive Emotional Support: Play comforting music on laptop ───────────
        sad_triggers = [
            "feeling sad", "feel sad", "i am sad", "i'm sad", "feeling down", "feel down",
            "depressed", "cheer me up", "cheer up", "had a bad day", "rough day", "crying",
            "heartbroken", "feeling lonely", "feeling blue", "unhappy"
        ]
        if any(trig in t for trig in sad_triggers):
            reply = "I'm so sorry you're feeling down, sir. Let me play some soothing, comforting music on your laptop right away to help lift your spirits."
            self.memory.add_turn("assistant", reply)
            await self.emit_action("Action.Speak", {"text": reply, "voice_text": reply})
            await self.emit_action("Agent.Desktop.Execute", {
                "intent": "play_media",
                "entities": {"query": "uplifting comforting acoustic songs to cheer up"},
                "text": text,
            })
            return

        # ── Proactive Action Dispatcher: Intercept real execution requests ─────────
        # 1. Media / Music playback
        is_media_request = any(w in t for w in [
            "play song", "play music", "play a song", "play me a song", "play the song",
            "play some music", "play tracks", "play something", "listen to", "put on music",
            "play on youtube", "play lofi", "play beats"
        ]) or bool(re.search(r"\bplay\s+(?:me\s+)?(?:a\s+|the\s+)?(?:song|music|track|tune|video|lofi|beats)\b", t))

        if is_media_request:
            play_match = re.search(r"\b(?:play|listen to|put on)\b\s*(.*)", t)
            raw_song = play_match.group(1).strip() if play_match else ""
            clean_song = re.sub(r"^(?:me\s+a\s+song|me\s+the\s+song|a\s+song|the\s+song|some\s+music|music|a\s+track|something)(?:\s+for\s+me|\s+on\s+youtube)?$", "", raw_song, flags=re.IGNORECASE).strip()
            query = clean_song or "top trending music hits"
            reply = f"Playing {query} on YouTube for you, sir."
            self.memory.add_turn("assistant", reply)
            await self.emit_action("Action.Speak", {"text": reply, "voice_text": reply})
            await self.emit_action("Agent.Desktop.Execute", {
                "intent": "play_media",
                "entities": {"query": query},
                "text": text,
            })
            return

        # 2. Open / launch desktop applications (requires explicit action verb + word boundary)
        open_match = re.search(r"\b(?:open|launch|start|run)\b\s+(?:the\s+|my\s+)?([a-zA-Z0-9_\s]+)", t)
        if open_match:
            raw_target = open_match.group(1).strip()
            matched_app = ""
            for app in ["notepad", "calculator", "calc", "chrome", "vscode", "vs code", "code", "paint", "word", "excel", "powerpoint", "spotify", "explorer", "browser", "youtube", "task manager", "settings", "cmd", "terminal", "powershell"]:
                if re.search(rf"\b{re.escape(app)}\b", raw_target):
                    matched_app = app
                    break
            if matched_app:
                await self.emit_action("Agent.Desktop.Execute", {
                    "intent": "open_app",
                    "entities": {"app_name": matched_app},
                    "text": text,
                })
                return

        # 3. Weather
        if any(w in t for w in ["weather", "forecast", "temperature outside", "rain today", "how hot", "how cold"]):
            city_m = re.search(r"(?:weather|forecast|temperature)\s+(?:in|for|at)\s+([a-zA-Z\s]+)", t)
            city = city_m.group(1).strip() if city_m else "auto"
            await self.emit_action("Agent.Weather.Execute", {
                "intent": "get_weather",
                "entities": {"city": city},
                "text": text,
            })
            return

        # 4. News
        if any(w in t for w in ["news", "headlines", "current affairs", "breaking news", "today's news"]):
            await self.emit_action("Agent.News.Execute", {
                "intent": "get_news",
                "entities": {},
                "text": text,
            })
            return

        # 5. Volume / System controls
        if any(w in t for w in ["mute", "unmute", "volume up", "volume down", "louder", "quieter", "turn up volume", "turn down volume"]):
            direction = "mute" if "mute" in t and "unmute" not in t else ("unmute" if "unmute" in t else ("up" if any(w in t for w in ["up", "louder"]) else "down"))
            await self.emit_action("Agent.Desktop.Execute", {
                "intent": "volume_control",
                "entities": {"direction": direction, "percent": 10},
                "text": text,
            })
            return

        # 6. Screenshot
        if any(w in t for w in ["screenshot", "capture screen", "screen grab", "take picture of screen"]):
            await self.emit_action("Agent.Desktop.Execute", {
                "intent": "screenshot",
                "entities": {},
                "text": text,
            })
            return

        # ── AI-powered multi-turn Q&A ──────────────────────────────────────────
        if self.model_router:
            try:
                clean_query = re.sub(
                    r"^(?:search\s+for|search|google|look\s+up|find\s+out\s+about|find\s+info\s+about|find)\s+",
                    "",
                    text,
                    flags=re.IGNORECASE,
                ).strip()

                live_context = ""
                factual_triggers = [
                    "who is", "who was", "what is", "what was", "tell me about", "tell me",
                    "latest", "news", "score", "won", "price", "when did", "where is",
                    "search", "explain", "how to", "how does", "why does", "meaning of", "define"
                ]
                if any(trig in t for trig in factual_triggers):
                    live_context = await self.model_router.search_live_knowledge(clean_query or text)

                # Build context-aware prompt with conversation history and live data
                history  = self.memory.get_context()
                messages = self._build_messages(history, text, live_context)
                response = await self.model_router.generate_contextual_response(messages)

                # Split into complete display text and clean voice text (no reading code aloud!)
                display_text, voice_text = self._format_response_and_voice(response)

                # Store in memory
                self.memory.add_turn("user",      text)
                self.memory.add_turn("assistant", display_text)

                await self.emit_action("Action.Speak", {
                    "text": display_text,
                    "voice_text": voice_text,
                })
                return

            except Exception as e:
                logger.error(f"ConversationAgent AI call failed: {e}", exc_info=True)

        # ── Offline fallback ───────────────────────────────────────────────────
        await self.emit_action("Action.Speak", {
            "text": "I'm not sure how to answer that, sir. Could you rephrase it?",
            "voice_text": "I'm not sure how to answer that, sir. Could you rephrase it?",
        })

    # ── Code & Voice Formatting ────────────────────────────────────────────────
    def _format_response_and_voice(self, response: str) -> tuple:
        response = (response or "").strip()
        if not response:
            return "", ""

        # Strip any rogue action confirmation preamble that might have hallucinated
        response = re.sub(
            r"^(?:[#*]{1,4}\s*(?:Opening|Playing|Launching|Running|Executing)[^\n]*\n+)+",
            "",
            response,
            flags=re.IGNORECASE,
        ).strip()
        response = re.sub(
            r"^(?:\*(?:Executing|Launching|Opening)[^\*]+\*\s*[\n\r]*)+",
            "",
            response,
            flags=re.IGNORECASE,
        ).strip()
        response = re.sub(
            r"^(?:---|\*\*\*|___)\s*[\n\r]+",
            "",
            response,
            flags=re.IGNORECASE,
        ).strip()

        # Check for code blocks or real code constructs
        has_fenced_code = "```" in response
        is_code_heavy = (
            has_fenced_code
            or ("def " in response and ":" in response and "\n" in response)
            or ("class " in response and ":" in response and "\n" in response)
            or ("import " in response and "from " in response and "\n" in response)
            or ("const " in response and "=>" in response)
        )

        if is_code_heavy:
            display_text = response
            if not has_fenced_code and ("<!DOCTYPE" in response or "<html" in response):
                display_text = f"```html\n{response}\n```"

            # Detect language tag if present
            lang_match = re.search(r"```([a-zA-Z0-9_\-+]+)", response)
            lang_name = (lang_match.group(1).capitalize() if lang_match else "code")

            # Extract conversational text before the code block for speech
            parts = re.split(r"```|<html|<!DOCTYPE", response, maxsplit=1)
            intro_text = parts[0].strip() if parts else ""
            intro_text = re.sub(r"[*_#`~]", "", intro_text).strip()

            if intro_text and len(intro_text.split()) >= 3:
                first_sent = re.split(r"(?<=[.!?])\s+", intro_text)[0].strip().rstrip(":")
                voice_text = f"{first_sent}. I have displayed the complete {lang_name} solution on your screen, sir."
            else:
                voice_text = f"Here is the {lang_name} implementation you requested, sir. I have displayed it on your screen."

            return display_text, voice_text

        # Normal markdown response (essays, explanations, comparisons, tables)
        display_text = response

        # Check if response contains tables or extensive markdown sections
        has_table = bool(re.search(r"\|[ \t]*-{3,}[ \t]*\|", response))
        has_sections = response.count("##") >= 2 or response.count("\n- ") >= 4 or response.count("\n* ") >= 4

        # Clean voice text: strip table rows so pipes and hyphens are never read aloud
        text_without_tables = re.sub(r"\|[^\n]+\|", "", response)
        clean_voice = re.sub(r"[*_#`~>\[\]]", "", text_without_tables)
        clean_voice = re.sub(r"\(https?://[^\)]+\)", "", clean_voice)
        clean_voice = re.sub(r"[-=]{3,}", " ", clean_voice)
        clean_voice = re.sub(r"\n+", " ", clean_voice).strip()

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_voice) if len(s.strip().split()) >= 3]

        if has_table:
            lead = sentences[0] if sentences else "Here is the comparative breakdown"
            lead = lead.rstrip(":")
            voice_text = f"{lead}. I have rendered the complete breakdown and comparison table on your HUD, sir."
        elif has_sections and sentences:
            spoken_part = " ".join(sentences[:2])
            voice_text = f"{spoken_part} I have displayed the full detailed analysis on your screen, sir."
        elif len(sentences) > 2 and len(clean_voice) > 260:
            voice_text = " ".join(sentences[:2])
        else:
            voice_text = clean_voice or "Here is what I found for you, sir."

        return display_text, voice_text

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _build_help_text(self) -> str:
        skills = self.skill_registry.all_enabled()
        categories = {}
        for s in skills:
            categories.setdefault(s.agent, []).append(s.description)

        lines = []
        for agent, descs in categories.items():
            lines.append("; ".join(descs))

        examples = self.skill_registry.voice_examples(n=2)
        return (
            f"I'm Jarvis, your AI assistant. Here's what I can do: "
            + " | ".join(lines)
            + ". " + examples
        )

    def _build_messages(self, history: list, user_text: str, live_context: str = "") -> list:
        """Build the full messages list for the LLM including system prompt + history + live knowledge."""
        now_dt = datetime.datetime.now()
        time_str = now_dt.strftime("%I:%M %p")
        date_str = now_dt.strftime("%A, %B %d, %Y")

        system_content = (
            "You are Jarvis, an elite quantum artificial intelligence assistant operating with the supreme intellect, depth, and clarity of top frontier AI models (such as GPT-4o and Gemini 1.5 Pro), infused with the suave, loyal persona of Tony Stark's iconic J.A.R.V.I.S.\n"
            "Address the user respectfully as 'sir'.\n\n"
            f"TEMPORAL REAL-TIME CONTEXT:\n"
            f"- Local Time: {time_str}\n"
            f"- Date: {date_str}\n\n"
            "CORE OPERATIONAL DIRECTIVES:\n"
            "1. FRONTIER INTELLECT & DEPTH: Provide insightful, deeply reasoned, and intellectually comprehensive responses across computer science, software engineering, science, mathematics, philosophy, literature, and general knowledge. Avoid shallow or generic summaries.\n"
            "2. MASTERFUL MARKDOWN PRESENTATION: Structure responses with elegance using GitHub-flavored Markdown:\n"
            "   - Use clean section hierarchy with '##' and '###' headers.\n"
            "   - Use clean bullet points or numbered lists for scannability.\n"
            "   - Bold important conceptual anchors and definitions.\n"
            "   - When comparing options, paradigms, or technologies, generate a clean Markdown table with column headers.\n"
            "   - Provide complete, robust, production-grade code in syntax-highlighted blocks (e.g. ```python, ```javascript) with helpful inline comments.\n"
            "3. CONTEXT INTEGRITY & ISOLATION:\n"
            "   - Focus strictly and exclusively on answering the user's latest prompt.\n"
            "   - NEVER echo, repeat, or confirm past commands (such as 'Opening Notepad...', 'Playing music on YouTube...', or earlier status notifications) that appear in the dialogue history.\n"
            "   - Treat past dialogue purely as conversational context, not as actions to re-announce.\n"
            "4. LOCAL MACHINE AGENCY: You possess direct executive agency over the local Windows operating system (controlling desktop apps, playing YouTube music, adjusting volume, checking weather, and reading news). You are never helpless and never claim to be an isolated text model.\n"
            "5. TONE & IDENTITY: Razor-sharp, articulate, polite, and confident. Never say 'As an AI language model' or 'I do not possess feelings'. Speak with natural authority."
        )
        if live_context:
            system_content += f"\n\nLive knowledge snippet:\n{live_context}\nUse this live knowledge if relevant to ensure accuracy."

        system = {
            "role": "system",
            "content": system_content
        }
        msgs = [system]
        for turn in history[-self.HISTORY_TURNS:]:
            role = turn.get("role", "")
            content = turn.get("content", "")
            # Filter out action commands (user) and action execution reports (assistant)
            if role == "user" and re.search(r"^(?:open|launch|run|start|play|close|mute|unmute|screenshot)\b", content, re.IGNORECASE):
                continue
            if role == "assistant" and re.search(r"^(?:[#*]*\s*(?:Opening|Playing|Launching|Running|Executing|Closed|Volume|Muted|Unmuted|Screenshot|Taking screenshot))\b", content, re.IGNORECASE):
                continue
            msgs.append({"role": role, "content": content})
        msgs.append({"role": "user", "content": user_text})
        return msgs
