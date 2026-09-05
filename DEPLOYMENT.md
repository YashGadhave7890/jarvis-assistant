# 🚀 JARVIS AI Assistant — Production Deployment Handbook

This comprehensive guide walks you through deploying the **JARVIS AI Assistant** across all major platforms: Windows Desktop, Docker containers, Cloud PaaS (Render / Railway / Fly.io), and Linux servers.

---

## 📋 Table of Contents
1. [Prerequisites & API Keys](#1-prerequisites--api-keys)
2. [Option 1: Windows 1-Click Native Desktop](#2-option-1-windows-1-click-native-desktop)
3. [Option 2: Local Network (LAN) & Mobile Access](#3-option-2-local-network-lan--mobile-access)
4. [Option 3: Containerized Deployment (Docker & Docker Compose)](#4-option-3-containerized-deployment-docker--docker-compose)
5. [Option 4: Cloud PaaS Deployment (Render / Railway / Fly.io)](#5-option-4-cloud-paas-deployment-render--railway--flyio)
6. [Option 5: Linux Server / Raspberry Pi (systemd)](#6-option-5-linux-server--raspberry-pi-systemd)
7. [Health Monitoring & Production Telemetry](#7-health-monitoring--production-telemetry)
8. [Troubleshooting & FAQs](#8-troubleshooting--faqs)

---

## 1. Prerequisites & API Keys

Jarvis requires Python 3.10 or 3.11 and free API keys. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Fill in your free API keys in `.env`:
* **Groq API Key (FREE)**: [console.groq.com/keys](https://console.groq.com/keys) — Powers the ultra-fast 120B model (`openai/gpt-oss-120b`).
* **OpenWeatherMap Key (FREE)**: [openweathermap.org/api](https://openweathermap.org/api) — Live weather conditions & forecasts.
* **NewsAPI Key (FREE)**: [newsapi.org/register](https://newsapi.org/register) — Real-time top headlines.

---

## 2. Option 1: Windows 1-Click Native Desktop

### ⚡ Method A: Double-Click Launcher (Easiest)
1. Simply double-click **`run_jarvis.bat`** in the project root folder.
2. The script will automatically:
   - Verify Python 3.10+ installation.
   - Create a Python virtual environment (`venv`).
   - Install or verify all dependencies from `requirements.txt`.
   - Launch the server at `http://127.0.0.1:8000` and automatically open your browser into the **Quantum HUD**.

### 🖥️ Method B: Create a Desktop Icon
To place a 1-click icon on your Windows Desktop:
1. Right-click **`create_desktop_shortcut.ps1`** and choose **Run with PowerShell**.
2. A shortcut named **JARVIS AI Assistant** will appear on your desktop. Double-clicking it launches Jarvis instantly!

---

## 3. Option 2: Local Network (LAN) & Mobile Access

Want to use Jarvis on your iPhone, Android phone, iPad, or another computer on the same Wi-Fi?

1. Find your computer's local IP address:
   ```cmd
   ipconfig
   # Look for "IPv4 Address", e.g., 192.168.1.150
   ```
2. Start Jarvis bound to all network interfaces:
   ```cmd
   python main.py --mode hud --host 0.0.0.0 --port 8000
   ```
3. Open your mobile browser (Safari, Chrome, Firefox) and navigate to:
   ```
   http://192.168.1.150:8000
   ```
4. Jarvis includes built-in **CORS middleware** and reactive mobile styling, allowing full chat and telemetry from any connected device!

---

## 4. Option 3: Containerized Deployment (Docker & Docker Compose)

Deploy Jarvis inside an isolated, production-ready container on any system (Windows, Mac, Linux, NAS, Synology, Unraid).

### Using Docker Compose (Recommended)
```bash
# 1. Build and start in the background
docker-compose up -d --build

# 2. View live logs
docker-compose logs -f

# 3. Stop the container
docker-compose down
```

### Using Standard Docker CLI
```bash
# 1. Build the multi-stage image
docker build -t jarvis-ai .

# 2. Run the container with persistent storage and .env file
docker run -d \
  --name jarvis_assistant \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  -v jarvis_data:/app/data \
  jarvis-ai
```

---

## 5. Option 4: Cloud PaaS Deployment (Render / Railway / Fly.io)

Jarvis is configured with dynamic `$PORT` detection and headless audio fallback, making it 100% compatible with free cloud platforms:

### Deploying to Render (render.com)

#### Recommended: 1-Click Blueprint or Docker Web Service
1. Push this repository to your GitHub account.
2. In the Render Dashboard, click **New +** → **Blueprint** (or **Web Service** → select **Docker**).
3. Connect your `jarvis-assistant` repository.
4. Render will automatically detect `render.yaml` and `Dockerfile`:
   - **Runtime**: `Docker` (ensures all audio libraries and C headers compile cleanly)
   - **Health Check Path**: `/health`
   - **Auto-Deploy**: Enabled on `main` branch push
5. In **Environment Variables**, provide your free API keys:
   - `GROQ_API_KEY`: `your_groq_api_key_here` (from [console.groq.com/keys](https://console.groq.com/keys))
   - `GROQ_MODEL`: `openai/gpt-oss-120b`
   - `OPENWEATHER_API_KEY`: `your_openweather_api_key_here` (optional)
   - `NEWS_API_KEY`: `your_newsapi_key_here` (optional)
6. Click **Apply / Deploy**. Your Jarvis assistant will be live at `https://<your-app>.onrender.com`!

#### Alternative: Native Python Service (`Procfile`)
If you choose the native Python runtime instead of Docker:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py --mode hud --host 0.0.0.0 --port $PORT --no-browser`

---

### 🌐 Cloud Render vs. 💻 Local Windows Capabilities

| Capability | 💻 Local Windows (`run_jarvis.bat`) | 🌐 Cloud Render (`https://...onrender.com`) |
| :--- | :---: | :---: |
| **Quantum HUD (60FPS Canvas)** | ✅ Full Interactive | ✅ Full Interactive |
| **Persistent WebSockets (`/ws`)** | ✅ Low-latency Local | ✅ Secure Proxy (`wss://`) |
| **Groq 120B AI Intelligence** | ✅ Frontier Speed | ✅ Frontier Speed |
| **Live Weather & Breaking News** | ✅ Real-time APIs | ✅ Real-time APIs |
| **Voice Input (Microphone)** | ✅ Physical PC Mic (`PyAudio`) | ✅ Browser Client Mic (`Web Speech API`) |
| **Voice Output (Audio)** | ✅ Physical PC Speakers (`Edge-TTS`) | ✅ Browser Audio Playback |
| **Desktop App Launching (Notepad, VS Code)** | ✅ Full OS Automation | ℹ️ Guided (Prompts local PC use) |
| **Desktop Screenshot & Volume Control** | ✅ Full OS Automation | ℹ️ Guided (Prompts local PC use) |
| **Memory Storage (`jarvis_memory.db`)** | ✅ Persistent Local SQLite | ⚠️ Session-based (Persistent with Render Disk) |

---

## 6. Option 5: Linux Server / Raspberry Pi (systemd)

For running Jarvis 24/7 on an Ubuntu, Debian, or Raspberry Pi server:

### 1-Click Installation Script
```bash
chmod +x deploy_linux.sh
./deploy_linux.sh
```

### Installing as a 24/7 Background System Service
```bash
# Copy systemd unit
sudo cp jarvis.service /etc/systemd/system/

# Reload systemd and start Jarvis
sudo systemctl daemon-reload
sudo systemctl enable --now jarvis

# Check service status
sudo systemctl status jarvis

# View live service logs
sudo journalctl -u jarvis -f
```

---

## 7. Health Monitoring & Production Telemetry

Jarvis includes a dedicated production health check endpoint at `/health`:

```bash
curl http://127.0.0.1:8000/health
```

**Sample Response:**
```json
{
  "status": "healthy",
  "service": "Jarvis AI Assistant",
  "version": "2.5.0",
  "uptime_seconds": 3614.2,
  "active_connections": 1,
  "audio_pipeline_active": true,
  "memory_mb": 114.5,
  "cpu_percent": 1.4,
  "model": "openai/gpt-oss-120b"
}
```

---

## 8. Troubleshooting & FAQs

### Q: Why do I see a warning about PyAudio on Linux / Docker?
**A**: Cloud instances and Docker containers don't have physical microphones attached. Jarvis automatically detects this and operates smoothly in **Web HUD Mode**, allowing text chat and browser WebSockets without crashing.

### Q: How do I change the speech rate or voice?
**A**: In `.env`, set `JARVIS_VOICE=en-US-GuyNeural` (male) or `JARVIS_VOICE=en-US-AriaNeural` (female), or any of the 100+ free high-definition Microsoft Edge-TTS voices.

### Q: How do I verify my deployment setup before launching?
**A**: Run the pre-flight verification tool:
```bash
python check_deployment.py
```
It tests your Python version, package imports, API keys, audio hardware, and static assets in 2 seconds.
