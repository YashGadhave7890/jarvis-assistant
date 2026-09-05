import os
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class LongTermMemory:
    """
    Persistent episodic memory using SQLite.
    Stores interaction history that can be retrieved by the Semantic layer or Agents.
    """
    def __init__(self, db_path: str = None):
        if db_path is None:
            env_db = os.environ.get("MEMORY_DB_PATH", "").strip()
            if env_db:
                self.db_path = env_db
            else:
                project_root = Path(__file__).resolve().parent.parent.parent
                self.db_path = str(project_root / "jarvis_memory.db")
        else:
            self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        role TEXT,
                        content TEXT,
                        metadata TEXT
                    )
                ''')
                conn.commit()
                logger.info("Long term memory database initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite DB: {e}")

    def store(self, role: str, content: str, metadata: str = "{}"):
        """Store a single memory episode."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO interactions (role, content, metadata) VALUES (?, ?, ?)",
                    (role, content, metadata)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")

    def fetch_recent(self, limit: int = 50):
        """Fetch recent episodes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT timestamp, role, content FROM interactions ORDER BY id DESC LIMIT ?", (limit,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to fetch memory: {e}")
            return []
