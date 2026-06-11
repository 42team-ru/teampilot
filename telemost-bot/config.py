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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
