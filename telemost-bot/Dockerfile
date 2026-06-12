FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /bin/uv

# System deps: PulseAudio, ffmpeg, Chromium prerequisites
RUN apt-get update && apt-get install -y --no-install-recommends \
    pulseaudio \
    xvfb \
    ffmpeg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-6 \
    libxext6 \
    libxcb1 \
    libxss1 \
    libxtst6 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Install Playwright's Chromium browser
RUN uv run playwright install chromium

COPY pulse/default.pa /etc/pulse/default.pa

COPY . .

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
