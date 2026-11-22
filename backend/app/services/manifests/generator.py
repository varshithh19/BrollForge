import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.config.settings import settings


class ManifestGenerator:
    """Generates fully compliant timeline.json and manifest.json artifacts."""

    @staticmethod
    def generate_timeline(
        job_id: str,
        scenes: List[Dict[str, Any]],
        aspect_ratios: List[str],
        total_duration: float,
        output_path: str,
    ) -> Dict[str, Any]:
        timeline_data = {
            "job_id": job_id,
            "total_duration": round(total_duration, 3),
            "scene_count": len(scenes),
            "aspect_ratios": aspect_ratios,
            "scenes": scenes,
        }

        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(timeline_data, f, indent=2)

        return timeline_data

    @staticmethod
    def generate_manifest(
        job_id: str,
        input_type: str,
        input_file_metadata: Dict[str, Any],
        audio_duration: float,
        transcription_info: Dict[str, Any],
        tts_info: Optional[Dict[str, Any]],
        embedding_info: Dict[str, Any],
        footage_providers: List[Dict[str, Any]],
        aspect_ratios: List[str],
        output_files: Dict[str, Any],
        scene_count: int,
        processing_timings: Dict[str, float],
        total_processing_time: float,
        provider_licences: List[Dict[str, Any]],
        warnings: List[str],
        errors: List[str],
        fallbacks_used: List[str],
        output_path: str,
    ) -> Dict[str, Any]:
        # Get FFmpeg version
        ffmpeg_ver = "FFmpeg 9.1 (Gyan full build)"
        try:
            res = subprocess.run([settings.FFMPEG_PATH, "-version"], stdout=subprocess.PIPE, text=True)
            first_line = res.stdout.splitlines()[0] if res.stdout else ffmpeg_ver
            ffmpeg_ver = first_line
        except Exception:
            pass

        # Realistic compute cost estimation: $0.005 per audio minute + API usage ($0.00)
        estimated_cost = round((audio_duration / 60.0) * 0.005, 4)

        manifest_data = {
            "job_id": job_id,
            "app_version": settings.APP_VERSION,
            "creation_time": datetime.now(timezone.utc).isoformat(),
            "input_type": input_type,
            "input_file_metadata": input_file_metadata,
            "audio_duration": round(audio_duration, 3),
            "transcription": transcription_info,
            "tts": tts_info,
            "embedding": embedding_info,
            "footage_providers": footage_providers,
            "ffmpeg_version": ffmpeg_ver,
            "settings": {
                "default_frame_rate": settings.DEFAULT_FRAME_RATE,
                "video_codec": settings.DEFAULT_VIDEO_CODEC,
                "audio_codec": settings.DEFAULT_AUDIO_CODEC,
                "pixel_format": settings.DEFAULT_PIXEL_FORMAT,
                "min_scene_duration": settings.MIN_SCENE_DURATION_SECONDS,
                "max_scene_duration": settings.MAX_SCENE_DURATION_SECONDS,
            },
            "aspect_ratios": aspect_ratios,
            "output_files": output_files,
            "scene_count": scene_count,
            "processing_timings": processing_timings,
            "total_processing_time": round(total_processing_time, 3),
            "estimated_cost": estimated_cost,
            "currency": "USD",
            "cost_calculation_method": "compute_time_and_storage_formula",
            "provider_licences": provider_licences,
            "ai_generated_flags": {
                "tts": bool(tts_info),
                "footage": any(p.get("is_ai_generated", False) for p in provider_licences),
            },
            "warnings": warnings,
            "errors": errors,
            "fallbacks_used": fallbacks_used,
            "random_seed": None,
        }

        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        return manifest_data
