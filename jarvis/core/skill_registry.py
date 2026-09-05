"""
Skill Registry — central catalogue of what Jarvis can do.
Each skill registers its name, agent, description, and example utterances.
Used by ConversationAgent to produce dynamic help and by the Orchestrator for routing hints.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    name: str
    agent: str
    description: str
    examples: List[str] = field(default_factory=list)
    enabled: bool = True


class SkillRegistry:
    """Global singleton that holds all registered Jarvis skills."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._register_defaults()

    def _register_defaults(self):
        defaults = [
            Skill("open_app",      "Desktop",      "Open any application",
                  ["open notepad", "launch chrome", "start calculator"]),
            Skill("close_app",     "Desktop",      "Close a running application",
                  ["close notepad", "kill chrome"]),
            Skill("play_media",    "Desktop",      "Play music or videos on YouTube",
                  ["play Bohemian Rhapsody", "play lofi music on youtube"]),
            Skill("web_search",    "Desktop",      "Search the web",
                  ["search for Python tutorials", "google latest news"]),
            Skill("compose_text",  "Desktop",      "Draft and type text in Notepad",
                  ["write a thank you letter", "type meeting notes"]),
            Skill("screenshot",    "Desktop",      "Take a screenshot",
                  ["take a screenshot", "capture screen"]),
            Skill("volume_control","Desktop",      "Control system volume",
                  ["volume up", "mute", "turn volume down"]),
            Skill("system_status", "System",       "Report CPU, RAM, disk, battery",
                  ["system status", "how much cpu am I using", "check battery"]),
            Skill("set_reminder",  "Reminder",     "Set a timed reminder",
                  ["remind me to take medicine in 10 minutes"]),
            Skill("get_weather",   "Weather",      "Check current weather",
                  ["what is the weather in Mumbai", "will it rain today"]),
            Skill("ask_ai",        "Conversation", "Answer general questions via AI",
                  ["what is quantum computing", "tell me a joke"]),
            Skill("greeting",      "Conversation", "Greet Jarvis",
                  ["hello jarvis", "good morning"]),
        ]
        for s in defaults:
            self.register(s)

    def register(self, skill: Skill):
        self._skills[skill.name] = skill
        logger.debug(f"Skill registered: {skill.name} → {skill.agent}")

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def all_enabled(self) -> List[Skill]:
        return [s for s in self._skills.values() if s.enabled]

    def help_text(self) -> str:
        """Build a concise spoken help string."""
        groups: Dict[str, List[str]] = {}
        for s in self.all_enabled():
            groups.setdefault(s.agent, []).append(s.description)
        parts = []
        for agent, descs in groups.items():
            parts.append("; ".join(descs))
        return "I can: " + ". I can also ".join(parts) + "."

    def voice_examples(self, n: int = 3) -> str:
        """Return n random example commands as a spoken string."""
        import random
        examples = []
        for s in self.all_enabled():
            examples.extend(s.examples)
        chosen = random.sample(examples, min(n, len(examples)))
        return "For example: " + ", or ".join(f'"{e}"' for e in chosen)
