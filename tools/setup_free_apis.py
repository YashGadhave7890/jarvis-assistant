#!/usr/bin/env python3
"""
JARVIS AI Assistant — Free API Configuration Wizard
Interactively helps users obtain and configure free API keys in .env.
Usage: python tools/setup_free_apis.py
"""

import os
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"
ENV_EXAMPLE = ROOT_DIR / ".env.example"


class FreeAPISetup:
    def __init__(self):
        self.env_file = ENV_FILE
        self.services = {
            "groq": {
                "name": "Groq Cloud (120B LLM)",
                "url": "https://console.groq.com/keys",
                "env_key": "GROQ_API_KEY",
                "description": "Ultra-fast frontier AI model (openai/gpt-oss-120b). 100% Free.",
                "steps": [
                    "1. Visit https://console.groq.com/keys",
                    "2. Sign up or log in with your GitHub/Google account",
                    "3. Click 'Create API Key'",
                    "4. Copy the key (starts with 'gsk_') and paste it below",
                ],
            },
            "openweather": {
                "name": "OpenWeatherMap",
                "url": "https://openweathermap.org/api",
                "env_key": "OPENWEATHER_API_KEY",
                "description": "Live weather conditions, temperature, and forecasts (1,000 calls/day free).",
                "steps": [
                    "1. Visit https://openweathermap.org/api",
                    "2. Sign up for a free tier account",
                    "3. Generate a free API key under 'My API Keys'",
                    "4. Copy the 32-character key and paste it below",
                ],
            },
            "newsapi": {
                "name": "NewsAPI",
                "url": "https://newsapi.org/register",
                "env_key": "NEWS_API_KEY",
                "description": "Real-time breaking news and top headlines (100 requests/day free).",
                "steps": [
                    "1. Visit https://newsapi.org/register",
                    "2. Register for a free Developer account",
                    "3. Copy your API key from the dashboard and paste it below",
                ],
            },
        }

    def run(self):
        print("\n" + "=" * 65)
        print("     JARVIS AI ASSISTANT — FREE API CONFIGURATION WIZARD     ")
        print("=" * 65)
        print("Configure free-tier API services to enable full Jarvis capabilities.\n")

        # Ensure .env exists
        if not self.env_file.exists():
            if ENV_EXAMPLE.exists():
                print(f"[INFO] Initializing .env from {ENV_EXAMPLE.name}...")
                self.env_file.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                self.env_file.touch()

        for service_id, config in self.services.items():
            self._setup_service(service_id, config)

        print("\n" + "=" * 65)
        print("🎉 Configuration complete! Your .env file is updated.")
        print("To launch Jarvis in Web HUD mode: python main.py --mode hud")
        print("=" * 65 + "\n")

    def _setup_service(self, service_id: str, config: dict):
        print(f"\n[SERVICE] {config['name']}")
        print(f"Details : {config['description']}")

        choice = input(f"Configure {config['name']}? (y/n) [default: y]: ").strip().lower()
        if choice in ["n", "no"]:
            print(f"Skipping {config['name']}.")
            return

        print("\nInstructions:")
        for s in config["steps"]:
            print(f"   {s}")

        open_browser = input(f"\nOpen {config['url']} in your browser now? (y/n): ").strip().lower()
        if open_browser in ["y", "yes"]:
            webbrowser.open(config["url"])

        key = input(f"\nEnter your {config['env_key']}: ").strip()
        if key:
            self._update_env(config["env_key"], key)
            print(f"✅ Saved {config['env_key']} to .env")
        else:
            print("No key entered. Skipping.")

    def _update_env(self, key: str, val: str):
        lines = []
        found = False
        if self.env_file.exists():
            lines = self.env_file.read_text(encoding="utf-8").splitlines()

        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}=") or line.strip().startswith(f"#{key}="):
                new_lines.append(f"{key}={val}")
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f"{key}={val}")

        self.env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    wizard = FreeAPISetup()
    wizard.run()
