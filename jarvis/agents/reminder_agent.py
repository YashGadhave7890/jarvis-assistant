"""
Reminder Agent — handles timed reminders set by voice.
Stores reminders in memory and fires them on the event bus when due.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List
from agents.base_agent import BaseAgent
from core.event_bus import EventBus

logger = logging.getLogger(__name__)

_UNIT_SECONDS = {
    "second": 1, "sec": 1,
    "minute": 60, "min": 60,
    "hour": 3600, "hr": 3600,
}


@dataclass
class Reminder:
    task: str
    fire_at: float   # time.monotonic() value when to fire


class ReminderAgent(BaseAgent):
    """
    Sets and manages countdown reminders.
    A background task fires them when due via 'Action.Speak'.
    """

    def __init__(self, event_bus: EventBus):
        super().__init__(name="Reminder", event_bus=event_bus)
        self._reminders: List[Reminder] = []
        self._watcher_running = False

    def start(self):
        """Start the background reminder watcher coroutine."""
        return asyncio.create_task(self._watcher_loop())

    async def execute(self, payload: dict):
        entities = payload.get("entities", {})
        task     = entities.get("task", "your reminder")
        amount   = int(entities.get("amount", 5))
        unit     = entities.get("unit", "minute")

        seconds = amount * _UNIT_SECONDS.get(unit.rstrip("s"), 60)
        fire_at = time.monotonic() + seconds

        self._reminders.append(Reminder(task=task, fire_at=fire_at))

        # Human-friendly confirmation
        if unit.startswith("sec"):
            time_str = f"{amount} second{'s' if amount > 1 else ''}"
        elif unit.startswith("min"):
            time_str = f"{amount} minute{'s' if amount > 1 else ''}"
        else:
            time_str = f"{amount} hour{'s' if amount > 1 else ''}"

        await self.emit_action("Action.Speak", {
            "text": f"Done sir! I'll remind you to {task} in {time_str}."
        })
        logger.info(f"Reminder set: '{task}' in {seconds}s")

    async def _watcher_loop(self):
        self._watcher_running = True
        while self._watcher_running:
            now = time.monotonic()
            due = [r for r in self._reminders if r.fire_at <= now]
            for r in due:
                logger.info(f"Reminder firing: '{r.task}'")
                await self.emit_action("Action.Speak", {
                    "text": f"Reminder sir! You wanted to: {r.task}"
                })
                self._reminders.remove(r)
            await asyncio.sleep(1)

    def stop(self):
        self._watcher_running = False
