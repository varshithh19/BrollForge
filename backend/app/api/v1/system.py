import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from backend.app.config.settings import settings
from backend.app.core.logging import logger
from backend.app.db.session import engine
from backend.app.services.footage.local_pack import LOCAL_LICENSED_CATALOG, LocalLicensedFootageProvider
from backend.app.services.footage.pexels_provider import PexelsProvider
from backend.app.services.footage.wikimedia_provider import WikimediaCommonsProvider

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@router.get("/ready", tags=["System"])
async def readiness_check():
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
            db_ok = True
    except Exception as e:
        logger.warning(f"Readiness DB probe failed: {e}")

    storage_ok = Path(settings.LOCAL_STORAGE_PATH).exists()

    is_ready = db_ok and storage_ok
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "database": "connected" if db_ok else "unreachable",
        "storage": "available" if storage_ok else "unavailable",
    }


@router.get("/api/v1/providers", tags=["Providers"])
async def list_providers():
    pexels = PexelsProvider()
    wikimedia = WikimediaCommonsProvider()
    local_pack = LocalLicensedFootageProvider()

    return {
        "primary_provider": {
            "name": pexels.name,
            "status": "active" if pexels.is_available else "disabled (API key required)",
            "license": pexels.LICENSE_NAME,
            "license_url": pexels.LICENSE_URL,
            "commercial_use_verified": True,
        },
        "secondary_provider": {
            "name": wikimedia.name,
            "status": "active",
            "license": "Creative Commons / Public Domain",
            "license_url": "https://commons.wikimedia.org/wiki/Commons:Licensing",
            "commercial_use_verified": True,
        },
        "local_licensed_pack": {
            "name": local_pack.name,
            "status": "active",
            "catalog_count": len(LOCAL_LICENSED_CATALOG),
            "license": "Creative Commons Zero (CC0 1.0 Universal)",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "commercial_use_verified": True,
        },
    }


@router.get("/api/v1/config", tags=["Configuration"])
async def get_system_config():
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "supported_aspect_ratios": ["16:9", "9:16", "1:1"],
        "default_aspect_ratios": settings.DEFAULT_ASPECT_RATIOS,
        "default_style": settings.DEFAULT_STYLE,
        "default_avoid": settings.DEFAULT_AVOID,
        "max_audio_duration_seconds": settings.MAX_AUDIO_DURATION_SECONDS,
        "default_tts_voice": settings.DEFAULT_TTS_VOICE,
        "supported_voices": [
            {"id": "en-IN-female", "name": "Indian English (Female - Neerja)", "native_code": "en-IN-NeerjaNeural"},
            {"id": "en-IN-male", "name": "Indian English (Male - Prabhat)", "native_code": "en-IN-PrabhatNeural"},
            {"id": "en-US-female", "name": "US English (Female - Aria)", "native_code": "en-US-AriaNeural"},
            {"id": "en-US-male", "name": "US English (Male - Guy)", "native_code": "en-US-GuyNeural"},
            {"id": "hi-IN-female", "name": "Hindi (Female - Swara)", "native_code": "hi-IN-SwaraNeural"},
            {"id": "ta-IN-female", "name": "Tamil (Female - Pallavi)", "native_code": "ta-IN-PallaviNeural"},
        ],
        "default_burn_captions": settings.DEFAULT_BURN_CAPTIONS,
        "default_generate_srt": settings.DEFAULT_GENERATE_SRT,
    }


@router.get("/api/v1/storage/{file_path:path}", tags=["Storage"])
async def serve_storage_file(file_path: str):
    base_dir = Path(settings.LOCAL_STORAGE_PATH).resolve()
    target_path = (base_dir / file_path).resolve()

    # Path traversal protection
    if not str(target_path).startswith(str(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied: path traversal prohibited")

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Determine media type
    ext = target_path.suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".srt": "text/plain",
        ".json": "application/json",
        ".jpg": "image/jpeg",
        ".png": "image/png",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(target_path, media_type=media_type)
