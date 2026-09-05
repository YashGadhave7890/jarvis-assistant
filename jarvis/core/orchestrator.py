"""
Upgraded Orchestrator — uses IntentClassifier instead of naive keyword matching.
Supports priority queuing, intent routing, and graceful fallback.
"""

import asyncio
import logging
import time
from core.event_bus import EventBus
from core.intent_classifier import IntentClassifier, Intent

logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self):
        self.queue = asyncio.PriorityQueue()
        self._seq = 0

    async def add_task(self, priority: int, task: dict):
        self._seq += 1
        await self.queue.put((priority, self._seq, task))


class Orchestrator:
    """
    Central Brain: receives Input.Text, classifies intent via NLP classifier,
    routes to the correct agent with structured payload including entities.
    """

    # Deduplication: ignore same text within this many seconds
    DEDUP_WINDOW = 1.5

    def __init__(self, event_bus: EventBus, model_router=None):
        self.bus          = event_bus
        self.model_router = model_router
        self.task_queue   = TaskQueue()
        self.classifier   = IntentClassifier()

        self.bus.subscribe("Input.Text",            self.handle_user_input)
        self.bus.subscribe("System.ActionComplete", self.handle_action_complete)

        self._running    = False
        self._last_text  = ""
        self._last_time  = 0.0

        # ── Pending context: last intent for follow-up detection ──────────────
        self._last_intent: str = ""

    # ── Public input handler ──────────────────────────────────────────────────
    async def handle_user_input(self, payload: dict):
        text = payload.get("text", "").strip()
        if not text:
            return

        # Deduplication guard (only within 1.5s)
        now = time.monotonic()
        if (text.lower() == self._last_text.lower()
                and (now - self._last_time) < self.DEDUP_WINDOW):
            logger.warning(f"Duplicate command ignored within window: '{text}'")
            return

        self._last_text = text
        self._last_time = now

        logger.info(f"Orchestrator received: '{text}'")
        await self.bus.publish("Jarvis.Thinking", {"text": text})
        await self.task_queue.add_task(1, {"type": "analyze_intent", "data": text})

    async def handle_action_complete(self, payload: dict):
        logger.debug(f"Action completed: {payload}")

    # ── Worker loop ───────────────────────────────────────────────────────────
    async def _worker_loop(self):
        self._running = True
        while self._running:
            try:
                priority, seq, task = await self.task_queue.queue.get()
                try:
                    if task["type"] == "analyze_intent":
                        await self._classify_and_route(task["data"])

                    elif task["type"] == "execute_agent":
                        await self.bus.publish(
                            f"Agent.{task['agent_name']}.Execute",
                            task["payload"],
                        )
                finally:
                    self.task_queue.queue.task_done()

            except asyncio.CancelledError:
                self._running = False
                break
            except Exception as e:
                logger.error(f"Orchestrator worker error: {e}", exc_info=True)

    # ── Intent classification + routing ───────────────────────────────────────
    async def _classify_and_route(self, text: str):
        intent: Intent = self.classifier.classify(text)

        agent_name = intent.agent
        intent_name = intent.name
        entities = intent.entities
        confidence = intent.confidence

        # If rule-based confidence is low, consult LLM for smart disambiguation
        if confidence < 0.7 and self.model_router:
            try:
                llm_parsed = await self.model_router.classify_intent_llm(text)
                if llm_parsed and llm_parsed.get("confidence", 0) >= 0.7:
                    logger.info(
                        f"LLM upgraded intent: '{intent_name}' ({confidence:.2f}) → "
                        f"'{llm_parsed['intent']}' ({llm_parsed['confidence']:.2f}) [Agent: {llm_parsed.get('agent')}]"
                    )
                    intent_name = llm_parsed.get("intent", intent_name)
                    agent_name  = llm_parsed.get("agent", agent_name)
                    entities    = llm_parsed.get("entities", entities)
                    confidence  = llm_parsed.get("confidence", confidence)
            except Exception as e:
                logger.debug(f"LLM intent fallback skipped: {e}")

        self._last_intent = intent_name

        # Build enriched payload for the agent
        agent_payload = {
            "text":       text,
            "intent":     intent_name,
            "entities":   entities,
            "confidence": confidence,
        }

        logger.info(
            f"Routing '{text}' → agent={agent_name} "
            f"intent={intent_name} conf={confidence:.2f}"
        )

        await self.bus.publish("Jarvis.Routed", {
            "agent": agent_name,
            "intent": intent_name,
            "confidence": confidence,
            "text": text,
        })

        await self.task_queue.add_task(
            2,
            {
                "type":       "execute_agent",
                "agent_name": agent_name,
                "payload":    agent_payload,
            },
        )

    def start(self):
        return asyncio.create_task(self._worker_loop())

    def stop(self):
        self._running = False
