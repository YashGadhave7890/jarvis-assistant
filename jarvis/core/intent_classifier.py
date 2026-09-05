"""
Advanced Intent Classifier — replaces simple keyword matching in the Orchestrator.
Uses weighted keyword scoring, entity extraction, and priority-based routing.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    name: str               # e.g. "play_music", "open_app", "ask_ai"
    agent: str              # e.g. "Desktop", "Conversation", "System"
    confidence: float       # 0.0 – 1.0
    entities: dict = field(default_factory=dict)   # extracted slots
    raw_text: str = ""


# ── Intent definitions ─────────────────────────────────────────────────────────
# Each entry: (intent_name, agent, [(keyword, weight), ...])
_INTENT_RULES = [
    # ── System diagnostics ────────────────────────────────────────────────
    ("system_status", "System", [
        ("system status", 1.0), ("cpu usage", 1.0), ("memory usage", 1.0),
        ("ram usage", 1.0),     ("disk space", 1.0), ("performance", 0.8),
        ("how is my pc", 0.9),  ("system info", 1.0), ("battery", 0.9),
        ("network", 0.7),       ("processes", 0.8),   ("temperature", 0.8),
    ]),
    # ── Emotional support & mood-based music actions ──────────────────────
    ("mood_action", "Desktop", [
        ("feeling sad", 1.8), ("feel sad", 1.8), ("i am sad", 1.8), ("i'm sad", 1.8),
        ("feeling down", 1.8), ("feel down", 1.8), ("feeling depressed", 1.8),
        ("depressed", 1.5), ("sad so play", 2.2), ("sad play", 2.0), ("sad song", 1.8),
        ("cheer me up", 2.0), ("cheer up", 1.8), ("crying", 1.5), ("had a bad day", 1.8),
        ("had a rough day", 1.8), ("heartbroken", 1.8), ("feeling lonely", 1.8),
        ("feeling blue", 1.8), ("i feel terrible", 1.5),
        ("feeling happy", 1.8), ("good mood", 1.8), ("let's celebrate", 1.8), ("party mood", 1.8),
        ("feeling stressed", 1.8), ("feel stressed", 1.8), ("calm me down", 1.8),
        ("relaxing music", 1.8), ("chill music", 1.8), ("can't sleep", 1.8),
        ("focus music", 1.8), ("study music", 1.8), ("coding music", 1.8),
    ]),
    # ── Media / YouTube ───────────────────────────────────────────────────
    ("play_media", "Desktop", [
        ("play",    1.5), ("play song", 2.5), ("play music", 2.5),
        ("play me a song", 2.8), ("play me the song", 2.8), ("play a song", 2.8),
        ("play the song", 2.8), ("play some music", 2.5),
        ("play tracks", 2.0), ("play tunes", 2.0), ("play something", 2.0),
        ("youtube", 1.8), ("listen to", 2.0), ("put on",  1.8),
        ("stream",  1.0), ("watch",    1.0),
    ]),
    # ── Open application ─────────────────────────────────────────────────
    ("open_app", "Desktop", [
        ("open notepad", 2.8), ("notepad", 2.2), ("open calculator", 2.8),
        ("calculator", 2.2), ("calc", 2.2), ("open chrome", 2.8),
        ("open vs code", 2.8), ("open paint", 2.8), ("open browser", 2.5),
        ("open",    1.8), ("launch", 1.8), ("start",   1.2),
        ("run",     1.0), ("load",   1.0), ("show me", 0.5),
    ]),
    # ── News & Headlines ──────────────────────────────────────────────────
    ("get_news", "News", [
        ("news", 2.0), ("latest news", 2.2), ("breaking news", 2.2),
        ("today's news", 2.2), ("tell me news", 2.5), ("tell me the news", 2.5),
        ("headlines", 2.2), ("top stories", 2.0), ("current affairs", 1.8),
    ]),
    # ── Weather ──────────────────────────────────────────────────────────
    ("get_weather", "Weather", [
        ("weather",     2.0), ("weather today", 2.5), ("what is the weather", 2.5),
        ("how is the weather", 2.5), ("temperature outside", 2.0), ("forecast", 2.0),
        ("will it rain", 2.0), ("sunny",   0.8), ("cloudy",   0.8),
        ("how hot",     1.5),  ("how cold", 1.5),
    ]),
    # ── Conversational / Q&A & Knowledge Search ───────────────────────────
    ("ask_ai", "Conversation", [
        ("search for", 1.0), ("search", 1.0), ("who is", 1.0), ("who was", 1.0),
        ("what is", 1.0), ("what was", 1.0), ("tell me about", 1.0), ("tell me", 0.8),
        ("explain", 1.0), ("look up", 0.9), ("find info", 0.9), ("find out", 0.9),
        ("how to", 0.9), ("how does", 0.9), ("why does", 0.9), ("why is", 0.9),
        ("when did", 0.9), ("where is", 0.9), ("calculate", 0.9), ("convert", 0.9),
        ("define", 0.9), ("meaning of", 0.9),
        ("what", 0.3), ("how", 0.3), ("why", 0.4), ("when", 0.4), ("who", 0.4),
    ]),
    # ── Greeting ─────────────────────────────────────────────────────────
    ("greeting", "Conversation", [
        ("hello", 1.0), ("hi jarvis", 1.0), ("hey",  0.9),
        ("good morning", 1.0), ("good evening", 1.0), ("good afternoon", 1.0),
    ]),
    # ── Farewell ─────────────────────────────────────────────────────────
    ("farewell", "Conversation", [
        ("goodbye", 1.0), ("bye",      1.0), ("see you",  0.9),
        ("shut up", 0.8), ("go away",  0.8), ("sleep",    0.7),
        ("that's all", 0.8), ("stop",  0.5),
    ]),
    # ── Volume control ───────────────────────────────────────────────────
    ("volume_control", "Desktop", [
        ("volume up", 1.0), ("volume down", 1.0), ("mute",       1.0),
        ("louder",    0.9), ("quieter",     0.9), ("unmute",     1.0),
        ("turn up",   0.8), ("turn down",   0.8),
    ]),
    # ── Screenshot / screen capture ──────────────────────────────────────
    ("screenshot", "Desktop", [
        ("screenshot", 1.0), ("capture screen", 1.0), ("take a picture of screen", 1.0),
        ("screen grab", 1.0), ("take screenshot", 1.0), ("capture the screen", 1.0),
    ]),
    # ── Multimodal screen vision & analysis ──────────────────────────────
    ("analyze_screen", "Desktop", [
        ("look at my screen", 3.0), ("look at the screen", 3.0), ("look at screen", 2.8),
        ("what is on my screen", 3.0), ("what's on my screen", 3.0), ("summarize my screen", 3.0),
        ("explain what is on my screen", 3.0), ("what error is this", 2.5), ("read my screen", 2.8),
        ("what am i looking at", 2.8), ("read this error", 2.5), ("check my screen", 2.5),
        ("see my screen", 2.5), ("describe my screen", 3.0), ("on my screen", 2.0),
        ("on the screen", 1.8), ("my screen", 1.6),
    ]),
    # ── Immediate stop / barge-in cancellation ───────────────────────────
    ("stop_speech", "Desktop", [
        ("stop talking", 1.0), ("stop speaking", 1.0), ("be quiet", 1.0),
        ("shut up", 1.0), ("silence", 1.0), ("cancel speech", 1.0), ("stop jarvis", 1.0),
        ("jarvis stop", 1.0), ("jarvis cancel", 1.0), ("quiet please", 0.9),
    ]),
    # ── Clipboard ────────────────────────────────────────────────────────
    ("clipboard", "Desktop", [
        ("copy to clipboard", 1.0), ("paste", 0.8), ("clipboard", 0.9),
    ]),
]


class IntentClassifier:
    """
    Scores each intent against user text using weighted keyword overlap.
    Returns the top-scoring Intent with extracted entities.
    """

    CONFIDENCE_THRESHOLD = 0.25   # Below this → fallback to "ask_ai"

    def __init__(self):
        self.rules = _INTENT_RULES
        logger.info(f"IntentClassifier ready with {len(self.rules)} intent patterns.")

    def classify(self, text: str) -> Intent:
        t = text.lower().strip()
        best_intent = "ask_ai"
        best_agent  = "Conversation"
        best_score  = 0.0

        for intent_name, agent, kw_list in self.rules:
            score = 0.0
            for kw, weight in kw_list:
                if kw in t:
                    # Reward longer (more specific) keyword matches
                    specificity = len(kw.split())
                    score += weight * (1.0 + 0.1 * specificity)
            if score > best_score:
                best_score  = score
                best_intent = intent_name
                best_agent  = agent

        # Normalise score to 0-1 range (cap at 1.0)
        confidence = min(best_score / 2.0, 1.0)

        if confidence < self.CONFIDENCE_THRESHOLD:
            best_intent = "ask_ai"
            best_agent  = "Conversation"

        entities = self._extract_entities(t, best_intent)

        result = Intent(
            name=best_intent,
            agent=best_agent,
            confidence=confidence,
            entities=entities,
            raw_text=text,
        )
        logger.info(
            f"Intent: '{best_intent}' → agent={best_agent} "
            f"confidence={confidence:.2f} entities={entities}"
        )
        return result

    # ── Entity extraction ──────────────────────────────────────────────────────
    def _extract_entities(self, t: str, intent: str) -> dict:
        entities = {}

        if intent == "mood_action":
            # Detect exact emotional state and provide smart music selection
            if any(w in t for w in ["sad", "down", "depress", "cry", "bad day", "rough day", "heartbroken", "lonely", "blue", "terrible", "cheer"]):
                entities["mood"] = "sad"
                entities["query"] = "uplifting comforting acoustic songs to cheer up"
                entities["spoken_intro"] = "I'm so sorry you're feeling down, sir. Let me play some comforting, uplifting music to help you relax and feel better."
            elif any(w in t for w in ["happy", "celebrat", "party", "dance", "good mood"]):
                entities["mood"] = "happy"
                entities["query"] = "upbeat energetic happy feel good songs"
                entities["spoken_intro"] = "Glad to hear you're in high spirits, sir! Putting on some celebratory upbeat music."
            elif any(w in t for w in ["stress", "calm", "relax", "chill", "sleep"]):
                entities["mood"] = "stressed"
                entities["query"] = "peaceful calming ambient relaxation music"
                entities["spoken_intro"] = "Take a moment to unwind, sir. Playing some calming, peaceful music for you right now."
            elif any(w in t for w in ["focus", "study", "code", "coding", "work"]):
                entities["mood"] = "focus"
                entities["query"] = "lofi hip hop radio beats to relax study to"
                entities["spoken_intro"] = "Entering focus mode, sir. Starting ambient lo-fi study beats."
            else:
                entities["mood"] = "neutral"
                entities["query"] = "soothing chill acoustic playlist"
                entities["spoken_intro"] = "Right away, sir. Putting on some soothing music on your laptop."

        elif intent == "play_media":
            # "play <song/artist> on youtube"
            m = re.search(r"\bplay\b\s+(.+?)(?:\s+on\s+|\s+in\s+|\s+for\s+|$)", t)
            raw_q = m.group(1).strip() if m else ""
            # Filter trivial fillers like "me a song", "a song", "some music", etc.
            cleaned_q = re.sub(r"^(?:me\s+a\s+song|a\s+song|some\s+music|music|a\s+track|something)(?:\s+accordingly)?$", "", raw_q, flags=re.IGNORECASE).strip()

            # If user mentioned an emotion in the play request (e.g. "I'm sad so play me a song")
            if any(w in t for w in ["sad", "down", "cry", "depress", "cheer"]):
                entities["query"] = "uplifting comforting songs to cheer up"
                entities["spoken_intro"] = "I understand you're feeling down, sir. Let me play some uplifting songs to cheer you up."
            elif any(w in t for w in ["relax", "chill", "calm", "sleep", "stress"]):
                entities["query"] = "relaxing peaceful lo-fi chill music"
                entities["spoken_intro"] = "Playing peaceful relaxation music for you, sir."
            elif any(w in t for w in ["happy", "party", "dance"]):
                entities["query"] = "upbeat energetic happy songs"
                entities["spoken_intro"] = "Playing upbeat energetic music, sir."
            elif cleaned_q:
                entities["query"] = cleaned_q
            else:
                entities["query"] = "popular trending music hits"

        elif intent == "web_search":
            # "search for <query>" or "google <query>"
            m = re.search(
                r"(?:search\s+for|google|look\s+up|browse\s+for|find)\s+(.+)", t
            )
            if m:
                entities["query"] = m.group(1).strip()

        elif intent == "open_app":
            m = re.search(r"(?:open|launch|start|run|load)\s+(?:the\s+|my\s+)?(.+)", t)
            raw_app = m.group(1).strip() if m else t
            entities["app_name"] = re.sub(r"\b(and all that|please|for me|and that|app|application)\b", "", raw_app, flags=re.IGNORECASE).strip()

        elif intent == "get_news":
            for cat in ["tech", "technology", "business", "sports", "science", "entertainment", "health", "world", "india", "ai"]:
                if cat in t:
                    entities["topic"] = cat
                    break

        elif intent == "close_app":
            m = re.search(r"(?:close|kill|terminate|exit|stop)\s+(.+)", t)
            if m:
                entities["app_name"] = m.group(1).strip()

        elif intent == "set_reminder":
            # "remind me to <task> in <time>" or "remind me at <time>"
            m = re.search(r"remind\s+me\s+(?:to\s+)?(.+?)(?:\s+in\s+|\s+at\s+|$)", t)
            if m:
                entities["task"] = m.group(1).strip()
            # Extract time
            time_m = re.search(
                r"(?:in\s+)?(\d+)\s*(minute|min|hour|hr|second|sec)", t
            )
            if time_m:
                entities["amount"] = int(time_m.group(1))
                entities["unit"]   = time_m.group(2)

        elif intent == "get_weather":
            m = re.search(r"(?:weather|forecast|temperature)\s+(?:in|for|at)\s+(.+)", t)
            if m:
                raw_city = m.group(1).strip()
                entities["city"] = re.sub(r"\b(today|now|please|for me|outside)\b", "", raw_city, flags=re.IGNORECASE).strip() or "auto"
            else:
                entities["city"] = "auto"

        elif intent == "volume_control":
            if "unmute" in t:
                entities["direction"] = "unmute"
            elif "mute" in t:
                entities["direction"] = "mute"
            elif "up" in t or "louder" in t or "increase" in t:
                entities["direction"] = "up"
            elif "down" in t or "quieter" in t or "decrease" in t or "lower" in t:
                entities["direction"] = "down"
            # percentage
            pct = re.search(r"(\d+)\s*(?:percent|%)", t)
            if pct:
                entities["percent"] = int(pct.group(1))

        elif intent == "compose_text":
            m = re.search(r"(?:write|type|draft|compose)\s+(?:a\s+)?(.+)", t)
            if m:
                entities["content"] = m.group(1).strip()

        return entities
