# voice-rvc — локальный OpenAI-совместимый TTS (edge-tts → RVC voice conversion).
# rvc-python тянет torch (тяжёлый образ ~неск. ГБ) — это нормально для CPU-инференса.
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RVC_MODELS_DIR=/app/rvc_models \
    PORT=5050

# ffmpeg — перекодирование mp3/wav и ресемплинг базового голоса
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app.py .

# Том для RVC-моделей (папка <name>/ с .pth + опц. .index)
VOLUME ["/app/rvc_models"]

EXPOSE 5050

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5050"]
