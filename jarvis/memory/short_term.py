import logging
from collections import deque
from typing import List, Dict

logger = logging.getLogger(__name__)

class ShortTermMemory:
    """
    Manages the sliding window context for the current session.
    Keeps track of recent user inputs and assistant responses.
    """
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        # Deque automatically pops oldest items when maxlen is reached
        self.history: deque = deque(maxlen=max_history)
        logger.info(f"Short term memory initialized (max {max_history} turns).")

    def add_turn(self, role: str, content: str):
        """Add a single conversational turn."""
        if role not in ["user", "assistant", "system"]:
            logger.warning(f"Invalid role '{role}' provided to memory.")
            return
            
        self.history.append({"role": role, "content": content})
        logger.debug(f"Added to memory [{role}]: {content[:30]}...")

    def get_context(self) -> List[Dict[str, str]]:
        """Retrieve the current conversation context formatted for LLMs."""
        return list(self.history)
        
    def clear(self):
        """Clear the current session memory."""
        self.history.clear()
        logger.info("Short term memory cleared.")
