from abc import ABC, abstractmethod
import asyncio
import logging
from core.event_bus import EventBus

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base class for all autonomous agents.
    Agents subscribe to their execution events and emit actions.
    """
    def __init__(self, name: str, event_bus: EventBus):
        self.name = name
        self.bus = event_bus
        
        # Subscribe to this agent's specific execute event
        self.bus.subscribe(f"Agent.{self.name}.Execute", self._handle_execute)
        
        logger.info(f"Agent '{self.name}' initialized.")

    async def _handle_execute(self, payload: dict):
        """Internal wrapper to handle the execution and catch errors."""
        try:
            logger.info(f"Agent '{self.name}' executing task...")
            result = await self.execute(payload)
            
            # Optionally publish that the agent finished its task
            await self.bus.publish(f"Agent.{self.name}.Complete", {"result": result})
            
        except Exception as e:
            logger.error(f"Agent '{self.name}' failed: {e}", exc_info=True)
            await self.bus.publish("System.Error", {"agent": self.name, "error": str(e)})

    @abstractmethod
    async def execute(self, payload: dict) -> any:
        """
        The core logic for the agent. Must be implemented by subclasses.
        Returns the result of the execution.
        """
        pass

    async def emit_action(self, action_type: str, data: dict):
        """Helper to emit an action event (e.g., Action.Desktop, Action.Speak)"""
        await self.bus.publish(action_type, data)
