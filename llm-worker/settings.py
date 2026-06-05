from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_GROUP_ID: str = "llm-worker"

    # LLM (Ollama OpenAI-compatible по умолчанию)
    LLM_API_BASE: str = "http://localhost:11434/v1"
    LLM_API_KEY: str = "ollama"
    LLM_CHEAP_MODEL: str = "mistral"
    LLM_EXPENSIVE_MODEL: str = "llama3.1:8b"

    # Cloud embeddings (OpenAI-compatible)
    EMBEDDINGS_API_BASE: str = "https://api.openai.com/v1"
    EMBEDDINGS_API_KEY: str = "sk-..."
    EMBEDDINGS_MODEL: str = "text-embedding-3-small"
    EMBEDDINGS_DIM: int = 1536

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_BATCHES: str = "message_batches"
    QDRANT_COLLECTION_TASKS: str = "tasks"
    DEDUP_THRESHOLD: float = 0.92
    STATUS_HINT_THRESHOLD: float = 0.70

    # Классификатор
    CLASSIFIER_THRESHOLD: float = 0.65
    AUTO_CONFIRM_THRESHOLD: float = 0.90

    # Параллелизм воркера
    LLM_WORKER_CONCURRENCY: int = 4

    # Чанкинг транскриптов
    TRANSCRIPT_CHUNK_CHARS: int = 6000
    TRANSCRIPT_CHUNK_OVERLAP_CHARS: int = 500

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False


settings = Settings()
