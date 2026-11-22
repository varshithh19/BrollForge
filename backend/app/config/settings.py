from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "BrollForge"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    SECRET_KEY: str = "dev-secret-key-incubrix-brollforge-2026-production-ready"
    WEBHOOK_SECRET: str = "incubrix-hmac-webhook-secret-key-32chars"
    API_KEY_RATE_LIMIT: str = "60/minute"

    DATABASE_URL: str = "sqlite:///./storage/brollforge.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    REDIS_URL: str = "redis://localhost:6379/0"
    QUEUE_NAME: str = "broll_render_queue"
    JOB_TIMEOUT_SECONDS: int = 600

    STORAGE_BACKEND: str = "local"
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_ACCESS_KEY: Optional[str] = "minioadmin"
    S3_SECRET_KEY: Optional[str] = "minioadmin"
    S3_BUCKET_NAME: str = "brollforge-artifacts"
    S3_REGION: str = "us-east-1"
    LOCAL_STORAGE_PATH: str = "./storage"

    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    def __init__(self, **values):
        super().__init__(**values)
        import shutil
        from pathlib import Path
        if not shutil.which(self.FFMPEG_PATH):
            winget_ffmpeg = Path(
                r"C:\Users\varshith2\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.1-full_build\bin\ffmpeg.exe"
            )
            if winget_ffmpeg.exists():
                self.FFMPEG_PATH = str(winget_ffmpeg)
        if not shutil.which(self.FFPROBE_PATH):
            winget_ffprobe = Path(
                r"C:\Users\varshith2\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.1-full_build\bin\ffprobe.exe"
            )
            if winget_ffprobe.exists():
                self.FFPROBE_PATH = str(winget_ffprobe)
    DEFAULT_FRAME_RATE: int = 30
    DEFAULT_VIDEO_CODEC: str = "libx264"
    DEFAULT_AUDIO_CODEC: str = "aac"
    DEFAULT_PIXEL_FORMAT: str = "yuv420p"
    MAX_AUDIO_DURATION_SECONDS: int = 600
    MIN_SCENE_DURATION_SECONDS: float = 2.0
    MAX_SCENE_DURATION_SECONDS: float = 10.0

    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    DEFAULT_TTS_VOICE: str = "en-IN-NeerjaNeural"
    TTS_PROVIDER: str = "edge-tts"

    FOOTAGE_PRIMARY_PROVIDER: str = "pexels"
    PEXELS_API_KEY: Optional[str] = None
    FOOTAGE_SECONDARY_PROVIDER: str = "local_pack"
    LOCAL_FOOTAGE_PATH: str = "./storage/licensed_footage_pack"

    EMBEDDING_PROVIDER: str = "tfidf_semantic"
    REUSE_PENALTY_FACTOR: float = 0.75

    DEFAULT_ASPECT_RATIOS: List[str] = ["16:9", "9:16", "1:1"]
    DEFAULT_STYLE: str = "bright, modern, real-world footage"
    DEFAULT_AVOID: List[str] = ["people's faces", "alcohol", "violence", "logos"]
    DEFAULT_BURN_CAPTIONS: bool = True
    DEFAULT_GENERATE_SRT: bool = True


settings = Settings()
