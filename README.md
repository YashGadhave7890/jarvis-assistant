# ⚡ JARVIS AI Assistant — Quantum Intelligence HUD

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Groq Cloud](https://img.shields.io/badge/Groq-120B_Model-f55036.svg)](https://console.groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](Dockerfile)
## 🌐 Live Preview

**[🚀 Open JARVIS AI Assistant — Live Demo](https://jarvis-assistant-gt4t.onrender.com)**

> **Deployed on Render** with WebSocket support and a cloud-compatible headless architecture.

> **Next-Generation Autonomous Artificial Intelligence Assistant featuring a 60FPS Reactive Quantum HUD, Continuous Low-Latency Voice, Multimodal Vision, and Local Operating System Agency.**

---

## 🌟 Key Highlights

* **🧠 Frontier-Grade Intelligence**: Powered by Groq's 120-Billion parameter open-weights model (`openai/gpt-oss-120b`), generating deep, multi-turn reasoning with GitHub-flavored Markdown, comparison tables, and syntax-highlighted code blocks with 1-click Copy buttons.
* **🎙️ Natural Voice & Single-Audio Pipeline**: High-definition Microsoft Edge-TTS audio with automatic spoken summaries and adaptive Noise Floor Voice Activity Detection (VAD).
* **🖥️ 60FPS Quantum Intelligence HUD**: High-tech cybernetic HUD built with glassmorphism, responsive ambient mesh glows, segmented listening mode controller (Continuous, Wake-Word, Push-to-Talk), live CPU/RAM telemetry, and real-time audio visualizer.
* **⚙️ Direct Windows Desktop Agency**: Autonomously launches desktop applications (Notepad, Calculator, Chrome, VS Code, Paint), controls system volume, plays YouTube music, and captures screenshots.
* **🌤️ Live Weather & Top News**: Real-time localized weather via OpenWeatherMap API and breaking news headlines via NewsAPI with automatic fallback providers.
* **🚀 Universal Multi-Platform Deployment**: Ready for 1-click Windows desktop execution, Docker containers, Cloud PaaS (Render, Railway, Fly.io), and Linux systemd daemons.

---

## 🏗️ System Architecture

```
                                  ┌───────────────────────────┐
                                  │   User Voice & Web HUD    │
                                  └─────────────┬─────────────┘
                                                │ WebSocket / HTTP
                                                ▼
                                  ┌───────────────────────────┐
                                  │   FastAPI ASGI Server     │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                CENTRAL ASYNC EVENT BUS                                  │
└───────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────┘
        │              │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼              ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│ Conversation ││   Desktop    ││    System    ││   Weather    ││     News     ││   Reminder   │
│    Agent     ││    Agent     ││    Agent     ││    Agent     ││    Agent     ││    Agent     │
└───────┬──────┘└──────┬───────┘└──────┬───────┘└──────┬───────┘└──────┬───────┘└──────┬───────┘
        │              │               │               │               │               │
        ▼              ▼               ▼               ▼               ▼               ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│  Groq 120B   ││ OS Windows   ││   psutil     ││ OpenWeather  ││   NewsAPI    ││ SQLite Memory│
│  ModelRouter ││ Automation   ││  Telemetry   ││     wttr     ││  DuckDuckGo  ││   Database   │
└──────────────┘└──────────────┘└──────────────┘└──────────────┘└──────────────┘└──────────────┘
```

---

## ⚡ Quickstart Guide

### 🪟 Windows 1-Click Launch (Easiest)
Simply double-click **`run_jarvis.bat`** in the project root folder.
The script will automatically check Python, create your virtual environment, verify dependencies, and open `http://127.0.0.1:8000` in your browser.

To add a 1-click icon to your desktop, right-click **`create_desktop_shortcut.ps1`** and choose **Run with PowerShell**.

---

### 💻 Manual CLI Installation

1. **Clone & Navigate**:
   ```bash
   git clone https://github.com/your-username/jarvis-ai-assistant.git
   cd jarvis-ai-assistant
   ```

2. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and add your API credentials locally. **Never commit the `.env` file** (it is strictly excluded in `.gitignore`):
   ```bash
   cp .env.example .env
   ```
   Add your free API keys in `.env`:
   * **`GROQ_API_KEY`**: Free at [console.groq.com/keys](https://console.groq.com/keys) (powers the frontier 120B model)
   * **`OPENWEATHER_API_KEY`**: Free at [openweathermap.org/api](https://openweathermap.org/api) (live weather; if omitted, Jarvis gracefully uses public fallback)
   * **`NEWS_API_KEY`**: Free at [newsapi.org/register](https://newsapi.org/register) (breaking headlines; if omitted, Jarvis uses DuckDuckGo news)

5. **Run Pre-flight Diagnostic Check**:
   ```bash
   python check_deployment.py
   ```

6. **Launch Jarvis**:
   ```bash
   python main.py --mode hud --port 8000
   ```
   Visit `http://127.0.0.1:8000` in your browser.

---

## 🐳 Docker & Cloud Deployment

### Docker Compose
```bash
# Start background container
docker-compose up -d --build

# View live logs
docker-compose logs -f
```

### Cloud Hosting (Render / Railway / Docker)
The project includes a production **`render.yaml`** Blueprint and **`Dockerfile`**, and automatically binds to dynamic cloud `$PORT` variables.
1. In Render, select **New +** → **Blueprint** and connect your repository.
2. Render automatically builds the containerized web service with full WebSocket (`/ws`) support.
3. Configure your environment variables (`GROQ_API_KEY`, etc.) in the Render dashboard.
4. Deploy! Jarvis will be live at `https://your-app.onrender.com`.

For full deployment documentation, see [**`DEPLOYMENT.md`**](DEPLOYMENT.md).

---

## 📂 Project Structure

```
Mini_ai_assistant/
├── .dockerignore                  # Docker build exclusions
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git secret & cache exclusions
├── check_deployment.py            # Pre-flight diagnostic tool
├── create_desktop_shortcut.ps1    # Desktop icon generator
├── DEPLOYMENT.md                  # Comprehensive deployment handbook
├── deploy_linux.sh                # 1-Click Linux installation script
├── Dockerfile                     # Multi-stage production container
├── docker-compose.yml             # Container orchestration
├── main.py                        # Unified application entry point
├── Procfile                       # Cloud PaaS descriptor
├── README.md                      # Project documentation
├── requirements.txt               # Production Python dependencies
├── run_jarvis.bat                 # Windows 1-click batch launcher
├── run_jarvis.ps1                 # Windows PowerShell launcher
├── jarvis.service                 # Linux systemd service daemon
├── tools/                         # Auxiliary diagnostic & setup tools
│   ├── __init__.py
│   ├── list_devices.py            # Audio hardware index discovery
│   ├── mic_test.py                # Microphone energy calibration
│   └── setup_free_apis.py         # Interactive API key wizard
└── jarvis/                        # Core Python Application Package
    ├── __init__.py
    ├── action/                    # OS desktop automation
    ├── agents/                    # Autonomous worker agents
    ├── core/                      # EventBus, Orchestrator, Intent Classifier
    ├── memory/                    # Short-term context & persistent SQLite
    ├── models/                    # ModelRouter with Groq failover
    ├── perception/                # Audio pipeline, Whisper STT, Edge-TTS, Vision
    ├── plugins/                   # Extensible plugin framework
    └── ui/                        # Web server & static Quantum HUD assets
```

---

## 🧪 Health Monitoring

Jarvis includes a live monitoring endpoint at `/health`:
```bash
curl http://127.0.0.1:8000/health
```

**Output:**
```json
{
  "status": "healthy",
  "service": "Jarvis AI Assistant",
  "version": "2.5.0",
  "uptime_seconds": 128.5,
  "active_connections": 1,
  "audio_pipeline_active": true,
  "memory_mb": 460.1,
  "cpu_percent": 1.2,
  "model": "openai/gpt-oss-120b"
}
```

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
