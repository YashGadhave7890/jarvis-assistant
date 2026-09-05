"""
News Agent — fetches breaking headlines using NewsAPI with DuckDuckGo fallback.
Provides curated top stories for HUD cards and natural voice briefings.
"""

import asyncio
import logging
import json
import os
import re
import urllib.request
import urllib.parse
from agents.base_agent import BaseAgent
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class NewsAgent(BaseAgent):
    """
    Handles 'get_news' intent.
    Uses NewsAPI (primary) and DuckDuckGo News (fallback).
    """

    def __init__(self, event_bus: EventBus):
        super().__init__(name="News", event_bus=event_bus)
        self.api_key = os.getenv("NEWS_API_KEY", "").strip()
        if not self.api_key:
            logger.info("NewsAgent: NEWS_API_KEY is not configured. Fallback to public news service will be used.")

    async def execute(self, payload: dict):
        text = payload.get("text", "")
        entities = payload.get("entities", {})
        topic = entities.get("topic", "")

        t = text.lower()
        if not topic:
            for cat in ["technology", "tech", "business", "sports", "science", "entertainment", "health", "world", "india", "ai"]:
                if cat in t:
                    topic = cat
                    break

        logger.info(f"NewsAgent: fetching news for topic='{topic or 'general'}'")

        try:
            display_text, voice_text = await asyncio.to_thread(self._fetch_news, topic)
        except Exception as e:
            logger.error(f"NewsAgent error: {e}", exc_info=True)
            display_text = (
                "I'm sorry sir, I couldn't retrieve the latest news headlines right now. "
                "Please check your internet connection."
            )
            voice_text = "I'm sorry sir, I couldn't retrieve the latest news headlines right now."

        await self.emit_action("Action.Speak", {
            "text": display_text,
            "voice_text": voice_text,
        })

    def _fetch_news(self, topic: str = "") -> tuple:
        articles = []

        # 1. Try NewsAPI
        if self.api_key:
            try:
                articles = self._fetch_newsapi(topic)
            except Exception as e:
                logger.warning(f"NewsAPI error: {e}. Trying DuckDuckGo fallback...")

        # 2. Fallback to DuckDuckGo News
        if not articles:
            try:
                articles = self._fetch_duckduckgo_news(topic or "top world headlines")
            except Exception as e:
                logger.warning(f"DuckDuckGo news error: {e}")

        if not articles:
            return (
                "No breaking news articles could be retrieved at this time, sir.",
                "I couldn't find any breaking news articles right now, sir."
            )

        # Build Display Text (Markdown)
        topic_header = f"Top {topic.title()} News" if topic else "Top Breaking News"
        lines = [f"**{topic_header}**\n"]
        voice_headlines = []

        for i, art in enumerate(articles[:3], 1):
            title = art.get("title", "").strip()
            source = art.get("source", "News")
            url = art.get("url", "")
            # Clean common trailing source tags from title (e.g. "Title - BBC News")
            clean_title = re.sub(r"\s*[-–|]\s*[^-–|]+$", "", title).strip() or title
            voice_headlines.append(f"Story {i}: {clean_title}.")

            if url:
                lines.append(f"{i}. [{clean_title}]({url}) — *{source}*")
            else:
                lines.append(f"{i}. **{clean_title}** — *{source}*")

        display_text = "\n".join(lines)
        voice_text = f"Here are the latest headlines, sir. " + " ".join(voice_headlines)

        return display_text, voice_text

    def _fetch_newsapi(self, topic: str) -> list:
        if not self.api_key:
            raise ValueError("NEWS_API_KEY is not configured.")
        # Category mapping for NewsAPI top-headlines
        categories = {"tech": "technology", "technology": "technology", "business": "business", "sports": "sports", "science": "science", "entertainment": "entertainment", "health": "health"}
        cat = categories.get(topic.lower(), "")

        if cat:
            url = f"https://newsapi.org/v2/top-headlines?category={cat}&language=en&pageSize=4&apiKey={self.api_key}"
        elif topic:
            encoded = urllib.parse.quote(topic)
            url = f"https://newsapi.org/v2/everything?q={encoded}&sortBy=publishedAt&language=en&pageSize=4&apiKey={self.api_key}"
        else:
            url = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=4&apiKey={self.api_key}"

        req = urllib.request.Request(url, headers={"User-Agent": "JarvisAI/2.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for a in data.get("articles", []):
            if a.get("title") and "[Removed]" not in a.get("title"):
                results.append({
                    "title": a["title"],
                    "source": a.get("source", {}).get("name", "News"),
                    "url": a.get("url", ""),
                })
        return results

    def _fetch_duckduckgo_news(self, query: str) -> list:
        from duckduckgo_search import DDGS
        results = []
        with DDGS(timeout=4) as ddgs:
            news_items = list(ddgs.news(query, max_results=3))
            for item in news_items:
                results.append({
                    "title": item.get("title", ""),
                    "source": item.get("source", "News"),
                    "url": item.get("url", ""),
                })
        return results
