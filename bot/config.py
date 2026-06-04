from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT_SECRET: str = "changeme"
    ADMIN_IDS: list[int] = []
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    BACKEND_URL: str = "http://127.0.0.1:8080"
    HTTP_TIMEOUT_SECONDS: float = 100.0
    HTTP_SLOW_REQUEST_MS: float = 500.0
    LOGIN_REDIRECT_URL: str = "http://localhost:8080/auth/telegram"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "uploads"
    MINIO_BUCKET_AUDIO: str = "audio-recordings"
    # Set to true to skip YouGile setup and use mock credentials
    MOCK_YOUGILE: bool = False
    MOCK_YOUGILE_TOKEN: str = "mock_token"
    MOCK_YOUGILE_BOARD_ID: str = "mock_board"

    class Config:
        env_file = ".env"


settings = Settings()
