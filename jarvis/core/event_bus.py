import asyncio
from typing import Callable, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """
    Central Async Event Bus.
    Subscribers are called SEQUENTIALLY (not concurrently) to prevent
    the same event from spawning parallel agent executions.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._queue   = asyncio.Queue()
        self._running = False

    def subscribe(self, topic: str, callback: Callable):
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        # Guard: never subscribe the same callback twice to the same topic
        if callback not in self._subscribers[topic]:
            self._subscribers[topic].append(callback)
            logger.debug(f"Subscribed {callback.__name__} to '{topic}'")

    async def publish(self, topic: str, payload: Any = None):
        logger.debug(f"Publishing '{topic}'")
        await self._queue.put((topic, payload))

    async def _process_events(self):
        self._running = True
        while self._running:
            try:
                topic, payload = await self._queue.get()

                if topic in self._subscribers:
                    for cb in self._subscribers[topic]:
                        try:
                            if asyncio.iscoroutinefunction(cb):
                                asyncio.create_task(self._safe_call_async(cb, topic, payload))
                            else:
                                asyncio.create_task(asyncio.to_thread(self._safe_call_sync, cb, topic, payload))
                        except Exception as e:
                            logger.error(f"Subscriber dispatch error on '{topic}': {e}", exc_info=True)

                self._queue.task_done()

            except asyncio.CancelledError:
                self._running = False
                break
            except Exception as e:
                logger.error(f"EventBus error on '{topic}': {e}", exc_info=True)

    async def _safe_call_async(self, cb: Callable, topic: str, payload: Any):
        try:
            await cb(payload)
        except Exception as e:
            logger.error(f"Async subscriber error on '{topic}': {e}", exc_info=True)

    def _safe_call_sync(self, cb: Callable, topic: str, payload: Any):
        try:
            cb(payload)
        except Exception as e:
            logger.error(f"Sync subscriber error on '{topic}': {e}", exc_info=True)

    def start(self):
        return asyncio.create_task(self._process_events())

    def stop(self):
        self._running = False
