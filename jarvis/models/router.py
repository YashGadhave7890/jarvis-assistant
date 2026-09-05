"""
Advanced Model Router — supports multi-turn conversation history,
dynamic fallback across Groq models, real-time web knowledge retrieval,
and LLM-assisted intent classification.
"""

import asyncio
import logging
import os
import json
import re
from typing import List, Dict, Optional, Any
from groq import AsyncGroq

logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "groq/compound-mini",
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-20b",
]


class ModelRouter:
    """
    Intelligent model router.
    - generate_response(prompt)            → single-turn
    - generate_contextual_response(msgs)   → multi-turn with message history & model failover
    - classify_intent_llm(text)            → zero-shot intent & entity parser
    - search_live_knowledge(query)         → web/wiki search for current facts
    """

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        self.groq_client = AsyncGroq(api_key=self.api_key) if self.api_key else None

        if self.groq_client:
            logger.info(f"ModelRouter: Groq ready, model={self.model}")
        else:
            logger.warning("ModelRouter: GROQ_API_KEY missing — offline mode.")

    # ── Single-turn ──────────────────────────────────────────────────────────
    async def generate_response(self, prompt: str, requires_complex_reasoning: bool = False) -> str:
        msgs = [
            {
                "role": "system",
                "content": (
                    "You are Jarvis, an advanced AI assistant. "
                    "Answer concisely in 1-3 sentences. "
                    "Address the user as 'sir'. "
                    "Never add preamble like 'Great question'."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        return await self.generate_contextual_response(msgs)

    # ── Multi-turn with failover ─────────────────────────────────────────────
    async def generate_contextual_response(self, messages: List[Dict], max_tokens: int = 3072) -> str:
        """
        Passes context to Groq for stateful conversation.
        Includes automatic failover across verified available models.
        """
        if not self.groq_client:
            return await self._offline_fallback()

        candidate_models = [self.model] + [m for m in FALLBACK_MODELS if m != self.model]

        for model_name in candidate_models:
            try:
                completion = await self.groq_client.chat.completions.create(
                    messages=messages,
                    model=model_name,
                    temperature=0.6,
                    max_tokens=max_tokens,
                    top_p=0.9,
                )
                response = completion.choices[0].message.content.strip()
                if model_name != self.model:
                    self.model = model_name
                    logger.info(f"Switched default Groq model to: {model_name}")
                logger.info(f"Groq response ({len(response)} chars) [{model_name}]: {response[:60]}…")
                return response
            except Exception as e:
                logger.warning(f"Groq model {model_name} failed: {e}. Trying next fallback...")

        return await self._offline_fallback()

    # ── Zero-shot LLM Intent Classification ──────────────────────────────────
    async def classify_intent_llm(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Uses Groq to classify ambiguous or complex user requests into structured intents.
        """
        if not self.groq_client:
            return None

        prompt = f"""
You are the central brain for Jarvis. Classify the user query into one of these intents:
1. "mood_action" (agent: "Desktop", for expressions of emotion like sadness, stress, happiness, or cheer me up, entities: {{"query": "soothing uplifting songs to cheer up"}})
2. "play_media" (agent: "Desktop", entities: {{"query": "song or artist"}})
3. "open_app" (agent: "Desktop", entities: {{"app_name": "app to open"}})
4. "close_app" (agent: "Desktop", entities: {{"app_name": "app to close"}})
5. "web_search" (agent: "Desktop", ONLY when user explicitly asks to open a browser window)
6. "compose_text" (agent: "Desktop", entities: {{"content": "text to type"}})
7. "volume_control" (agent: "Desktop", entities: {{"direction": "up|down|mute|unmute", "percent": 0-100}})
8. "get_weather" (agent: "Weather", entities: {{"city": "city name or auto"}})
9. "get_news" (agent: "News", entities: {{"topic": "tech|business|sports|world|general"}})
10. "system_status" (agent: "System", entities: {{}})
11. "set_reminder" (agent: "Reminder", entities: {{"task": "task", "amount": number, "unit": "second|minute|hour"}})
12. "ask_ai" (agent: "Conversation", for general questions or explanations)

User query: "{text}"

Return ONLY a JSON object with this exact schema:
{{"intent": "<intent_name>", "agent": "<agent_name>", "confidence": 0.0-1.0, "entities": {{}}}}
"""
        try:
            raw_json = await self.extract_json(prompt)
            data = json.loads(raw_json)
            if "intent" in data and "agent" in data:
                return data
        except Exception as e:
            logger.debug(f"LLM intent classification skipped: {e}")
        return None

    # ── Live Knowledge Retrieval ─────────────────────────────────────────────
    async def search_live_knowledge(self, query: str) -> str:
        """
        Searches DuckDuckGo and Wikipedia for live information to ground answers.
        """
        try:
            return await asyncio.wait_for(asyncio.to_thread(self._sync_search, query), timeout=4.0)
        except Exception:
            return ""

    def _sync_search(self, query: str) -> str:
        # Clean filler prefixes
        clean_q = re.sub(r"^(?:who is|who was|what is|what was|tell me about|information about)\s+", "", query, flags=re.IGNORECASE).strip() or query

        # Try Wikipedia first for biographical / encyclopedia queries
        if any(w in query.lower() for w in ["who is", "who was", "what is", "tell me about", "biography"]):
            try:
                import wikipedia
                wikipedia.set_user_agent("JarvisAssistant/2.0 (contact@example.com)")
                summary = wikipedia.summary(clean_q, sentences=2)
                if summary:
                    return summary
            except Exception:
                pass

        # Try DuckDuckGo
        try:
            from duckduckgo_search import DDGS
            with DDGS(timeout=3) as ddgs:
                results = list(ddgs.text(clean_q, max_results=2))
                if results:
                    snippets = [r.get("body", "") for r in results if r.get("body")]
                    if snippets:
                        return "\n".join(snippets)
        except Exception:
            pass

        return ""

    # ── Tool calling helper ──────────────────────────────────────────────────
    async def extract_json(self, prompt: str, schema_hint: str = "") -> str:
        """Ask Groq to return structured JSON."""
        sys_prompt = (
            "You are a strict JSON extractor. "
            "Return ONLY valid raw JSON. "
            "Never use markdown code blocks, backticks, or explanatory text."
        )
        if schema_hint:
            sys_prompt += f" Schema: {schema_hint}"
        raw = await self.generate_contextual_response([
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": prompt},
        ])
        # Strip markdown ```json ... ``` if model included them
        clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)
        return clean.strip()

    async def _offline_fallback(self) -> str:
        return (
            "I'm sorry sir, my AI brain is currently offline. "
            "Please verify your internet connection or check your Groq API key."
        )
