import io

from openai import OpenAI

from settings import settings

_client = OpenAI(
    base_url=settings.WHISPER_API_BASE,
    api_key=settings.WHISPER_API_KEY,
    timeout=settings.WHISPER_TIMEOUT_SECONDS,
    max_retries=1,
)


def transcribe(audio_bytes: bytes, filename: str) -> str:
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename
    response = _client.audio.transcriptions.create(
        model=settings.WHISPER_MODEL,
        file=audio_file,
        language=settings.WHISPER_LANGUAGE,
        response_format="text",
        temperature=0.0,
    )
    return response if isinstance(response, str) else response.text
