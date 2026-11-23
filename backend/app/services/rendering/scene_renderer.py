import os
import subprocess
from pathlib import Path
from typing import Any, Dict
from backend.app.config.settings import settings
from backend.app.core.errors import RenderingError
from backend.app.core.logging import logger
from backend.app.services.rendering.aspect_converter import build_aspect_filter


class SceneRenderer:
    """Renders normalized aspect-ratio-specific scene segments using FFmpeg."""

    @staticmethod
    def render_scene_segment(
        raw_clip_path: str,
        duration: float,
        aspect_ratio: str,
        output_path: str,
    ) -> str:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        aspect_filter = build_aspect_filter(aspect_ratio)
        dur_str = f"{duration:.3f}"

        # FFmpeg command: stream_loop ensures clips shorter than scene duration loop seamlessly
        cmd = [
            settings.FFMPEG_PATH,
            "-y",
            "-stream_loop", "-1",
            "-i", raw_clip_path,
            "-t", dur_str,
            "-vf", aspect_filter,
            "-c:v", settings.DEFAULT_VIDEO_CODEC,
            "-threads", "2",
            "-preset", "ultrafast",
            "-pix_fmt", settings.DEFAULT_PIXEL_FORMAT,
            "-r", str(settings.DEFAULT_FRAME_RATE),
            "-an",  # Strip footage source audio (narration will be mixed over in composer)
            str(target),
        ]

        logger.info(f"Rendering scene segment: {target.name} ({aspect_ratio}, {dur_str}s)")
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg scene render error: {e.stderr}")
            raise RenderingError(f"Failed to render scene segment: {e.stderr}", details={"stderr": e.stderr})

        return str(target)
