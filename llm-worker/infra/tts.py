"""Text-to-speech через OpenRouter /audio/speech (OpenAI-совместимо).

Озвучивает короткий ответ голосового ассистента. Ключ по умолчанию — тот же
OpenRouter-ключ, что и для LLM (settings.LLM_API_KEY)."""
from __future__ import annotations

from openai import OpenAI

from settings import settings

_client = OpenAI(
    base_url=settings.TTS_API_BASE,
    api_key=settings.TTS_API_KEY or settings.LLM_API_KEY,
    timeout=settings.TTS_TIMEOUT_SECONDS,
    max_retries=1,
)


def synthesize(text: str) -> bytes:
    """Синтезирует речь и возвращает аудио-байты в формате settings.TTS_FORMAT (mp3 по умолчанию)."""
    response = _client.audio.speech.create(
        model=settings.TTS_MODEL,
        voice=settings.TTS_VOICE,
        input=text,
        response_format=settings.TTS_FORMAT,
    )
    # openai>=1.0: HttpxBinaryResponseContent — .content отдаёт сырые байты
    return response.content
