# ===================================================================
# JARVIS AI ASSISTANT — Production Multi-Stage Dockerfile
# Optimized for Cloud, VPS, and Local Docker Deployment
# ===================================================================

# ── Stage 1: Build Dependencies ─────────────────────────────────────
FROM python:3.11-slim as builder

WORKDIR /app

# Install build tools and audio library development headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    portaudio19-dev \
    libasound2-dev \
    libsndfile1-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Final Lean Runtime Image ──────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install runtime libraries for audio and networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    libasound2 \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project source code
COPY . .

# Run under dedicated non-root user for security
RUN useradd -m -u 1000 jarvisuser && \
    chown -R jarvisuser:jarvisuser /app
USER jarvisuser

# Default runtime configuration
ENV PORT=8000 \
    HOST=0.0.0.0 \
    JARVIS_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Container Healthcheck against /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8000}/health || exit 1

# Launch in server HUD mode (dynamically binds to Render's $PORT or defaults to 8000)
CMD ["python", "main.py", "--mode", "hud", "--host", "0.0.0.0", "--no-browser"]
