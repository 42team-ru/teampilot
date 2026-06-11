from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT_SECRET: str = "changeme"
    ADMIN_IDS: list[int] = [713978344,2031863132,1763162562,5288131710]
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    BACKEND_URL: str = "http://127.0.0.1:8080"
    HTTP_TIMEOUT_SECONDS: float = 100.0
    HTTP_CONNECT_TIMEOUT_SECONDS: float = 5.0
    HTTP_SOCK_READ_TIMEOUT_SECONDS: float = 30.0
    HTTP_SLOW_REQUEST_MS: float = 500.0
    HTTP_TRACE_PHASE_MS: float = 100.0
    HTTP_FORCE_IPV4: bool = True 
    EVENT_LOOP_LAG_WARN_MS: float = 250.0
    EVENT_LOOP_LAG_INTERVAL_SECONDS: float = 0.5
    UPDATE_SLOW_HANDLER_MS: float = 1000.0
    KAFKA_SLOW_PUBLISH_MS: float = 250.0
    LOGIN_REDIRECT_URL: str = "http://localhost:8080/auth/telegram"
    MINI_APP_URL: str = "https://42team.ru/app"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "uploads"
    MINIO_BUCKET_AUDIO: str = "audio-recordings"
    LLM_WORKER_URL: str = "http://localhost:8001"
    # Set to true to skip YouGile setup and use mock credentials
    MOCK_YOUGILE: bool = False
    MOCK_YOUGILE_TOKEN: str = "mock_token"
    MOCK_YOUGILE_BOARD_ID: str = "mock_board"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
