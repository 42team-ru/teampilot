from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BACKEND_URL: str = "http://localhost:8080"
    BOT_SECRET: str = "changeme"
    CHUNK_SECONDS: int = 30
    SAMPLE_RATE: int = 16000
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "audio"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    CHUNKS_DEBUG_DIR: str = ""  # если пустая строка — не сохранять локально

    # ── Голосовой Q&A («Пилот, ...») ──
    VOICE_QA_ENABLED: bool = True
    WORKER_URL: str = "http://localhost:8001"          # llm-worker HTTP API
    # STT для wake-детекта + вопроса (Groq, OpenAI-совместимый)
    WHISPER_API_BASE: str = "https://api.groq.com/openai/v1"
    WHISPER_API_KEY: str = ""
    WHISPER_MODEL: str = "whisper-large-v3"
    WHISPER_LANGUAGE: str = "ru"
    WAKE_WORDS: str = "пилот,pilot"                    # через запятую (для WAKE_MODE=stt)
    # Режим детекта триггера: "stt" (always-listen+Whisper) | "openwakeword" (локальный движок)
    WAKE_MODE: str = "stt"
    OWW_MODEL_PATH: str = ""                            # путь к кастомной .onnx («пилот»); пусто → встроенные модели
    OWW_THRESHOLD: float = 0.5
    OWW_INFERENCE_FRAMEWORK: str = "onnx"               # onnx | tflite
    VAD_AGGRESSIVENESS: int = 2                         # 0..3, выше = агрессивнее режет тишину
    VAD_SILENCE_MS: int = 700                           # пауза, считающаяся концом фразы
    MIN_UTTERANCE_MS: int = 600                         # короче — игнорируем (шум)
    MAX_UTTERANCE_MS: int = 12000                       # длиннее — форс-обрыв
    VOICE_REPLY_TIMEOUT_SECONDS: int = 25               # бюджет ответа воркера

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
