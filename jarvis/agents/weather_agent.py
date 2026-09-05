"""
Weather Agent — fetches live weather using OpenWeather API with wttr.in fallback.
Provides accurate current temperatures, weather conditions, humidity, and wind.
"""

import asyncio
import logging
import json
import os
import urllib.request
import urllib.parse
import urllib.error
from agents.base_agent import BaseAgent
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class WeatherAgent(BaseAgent):
    """
    Handles 'get_weather' intent.
    Uses OpenWeather API (primary) and wttr.in JSON API (fallback).
    """

    DEFAULT_CITY = "auto"

    def __init__(self, event_bus: EventBus):
        super().__init__(name="Weather", event_bus=event_bus)
        self.api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
        if not self.api_key:
            logger.info("WeatherAgent: OPENWEATHER_API_KEY is not configured. Fallback to public weather service will be used.")

    async def execute(self, payload: dict):
        entities = payload.get("entities", {})
        city = entities.get("city", "").strip() or self.DEFAULT_CITY

        # Clean city name if extracted from conversational text
        if city and city.lower() not in ["auto", "current", "here", "today", "my area"]:
            city = city.replace("today", "").replace("now", "").replace("please", "").strip()
        else:
            city = "auto"

        logger.info(f"WeatherAgent: fetching weather for target='{city}'")

        try:
            display_text, voice_text = await asyncio.to_thread(self._fetch_weather_unified, city)
        except Exception as e:
            logger.error(f"WeatherAgent error: {e}", exc_info=True)
            display_text = (
                "I'm sorry sir, I couldn't fetch the weather right now. "
                "Please check your internet connection."
            )
            voice_text = "I'm sorry sir, I couldn't retrieve the live weather report right now."

        await self.emit_action("Action.Speak", {
            "text": display_text,
            "voice_text": voice_text,
        })

    def _fetch_weather_unified(self, city: str) -> tuple:
        # Determine actual city query
        resolved_city = city
        if city == "auto":
            detected = self._detect_city_by_ip()
            resolved_city = detected or "London"

        # Try OpenWeather API first
        if self.api_key:
            try:
                res = self._fetch_openweather(resolved_city)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"OpenWeather failed: {e}. Trying wttr.in fallback...")

        # Fallback to wttr.in
        try:
            return self._fetch_wttr(resolved_city)
        except Exception as e2:
            logger.error(f"wttr.in fallback also failed: {e2}")

        return (
            f"Weather information for {resolved_city.title()} is temporarily unavailable.",
            f"Weather information for {resolved_city.title()} is currently unavailable, sir."
        )

    def _detect_city_by_ip(self) -> str:
        """Fast IP geolocation to find user's current city."""
        for endpoint in [
            "https://ipapi.co/city/",
            "http://ip-api.com/json/?fields=city",
        ]:
            try:
                req = urllib.request.Request(endpoint, headers={"User-Agent": "Jarvis/2.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = resp.read().decode("utf-8").strip()
                    if data.startswith("{"):
                        js = json.loads(data)
                        if js.get("city"):
                            return js["city"]
                    elif data and len(data) < 40 and not data.startswith("<"):
                        return data
            except Exception:
                pass
        return ""

    def _fetch_openweather(self, city: str) -> tuple:
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY is not configured.")
        encoded = urllib.parse.quote(city)
        url = f"https://api.openweathermap.org/data/2.5/weather?q={encoded}&appid={self.api_key}&units=metric"
        req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        city_name = data.get("name", city.title())
        country   = data.get("sys", {}).get("country", "")
        loc_str   = f"{city_name}, {country}" if country else city_name

        weather_desc = data.get("weather", [{}])[0].get("description", "clear sky").capitalize()
        main = data.get("main", {})
        temp = round(main.get("temp", 0), 1)
        feels_like = round(main.get("feels_like", temp), 1)
        temp_min = round(main.get("temp_min", temp), 1)
        temp_max = round(main.get("temp_max", temp), 1)
        humidity = main.get("humidity", 0)
        wind_kmh = round(data.get("wind", {}).get("speed", 0) * 3.6, 1)

        display_text = (
            f"**Current Weather for {loc_str}**\n\n"
            f"- **Conditions**: {weather_desc}\n"
            f"- **Temperature**: {temp}°C (Feels like {feels_like}°C)\n"
            f"- **Daily Range**: {temp_min}°C – {temp_max}°C\n"
            f"- **Humidity**: {humidity}%\n"
            f"- **Wind Speed**: {wind_kmh} km/h"
        )

        voice_text = (
            f"The weather in {city_name} is currently {weather_desc.lower()} at {temp} degrees Celsius, "
            f"feels like {feels_like}. Humidity is {humidity} percent with winds at {wind_kmh} kilometers per hour."
        )

        return display_text, voice_text

    def _fetch_wttr(self, city: str) -> tuple:
        encoded = urllib.parse.quote(city) if city != "auto" else ""
        url = f"https://wttr.in/{encoded}?format=j1" if encoded else "https://wttr.in/?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "JarvisAI/2.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        current = data["current_condition"][0]
        desc    = current["weatherDesc"][0]["value"]
        temp_c  = current["temp_C"]
        feels   = current["FeelsLikeC"]
        humid   = current["humidity"]
        wind    = current["windspeedKmph"]

        nearest = data.get("nearest_area", [{}])[0]
        area    = nearest.get("areaName", [{}])[0].get("value", city.title())
        country = nearest.get("country", [{}])[0].get("value", "")
        loc_str = f"{area}, {country}".strip(", ") if country else area

        display_text = (
            f"**Current Weather for {loc_str}**\n\n"
            f"- **Conditions**: {desc}\n"
            f"- **Temperature**: {temp_c}°C (Feels like {feels}°C)\n"
            f"- **Humidity**: {humid}%\n"
            f"- **Wind Speed**: {wind} km/h"
        )
        voice_text = f"Current weather in {area}: {desc} at {temp_c} degrees Celsius, feels like {feels} degrees."
        return display_text, voice_text
