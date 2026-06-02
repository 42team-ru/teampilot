from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    BACKEND_URL: str = "http://localhost:8080"
    LOGIN_REDIRECT_URL: str = "http://localhost:8080/auth/telegram"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_AUDIO: str = "audio-recordings"

    class Config:
        env_file = ".env"


settings = Settings()
