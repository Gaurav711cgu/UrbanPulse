from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    ENV: Literal["development", "production", "test"] = "development"
    DATABASE_URL: str = "postgresql+asyncpg://urbanpulse:urbanpulse@localhost:5432/urbanpulse"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "changeme-in-production-use-secrets-manager"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ML model paths
    YOLO_WEIGHTS: str = "weights/yolov8n_traffic.pt"
    LSTM_WEIGHTS: str = "weights/lstm_forecaster.pt"
    DQN_WEIGHTS: str = "weights/dqn_agent.pt"

    # Signal control
    SIGNAL_CYCLE_SECONDS: int = 90
    MIN_GREEN_SECONDS: int = 10
    MAX_GREEN_SECONDS: int = 60
    EMERGENCY_OVERRIDE_SECONDS: int = 120

    # Simulation
    NUM_JUNCTIONS: int = 16
    MOCK_DATA_INTERVAL_MS: int = 2000

    class Config:
        env_file = ".env"


settings = Settings()
