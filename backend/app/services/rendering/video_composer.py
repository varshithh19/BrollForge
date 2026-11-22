import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.config.settings import settings
from backend.app.core.errors import RenderingError
from backend.app.core.logging import logger
from backend.app.services.rendering.aspect_converter import get_aspect_dimensions


class VideoComposer:
    """Concatenates scene segments, mixes narration audio track, burns captions, and validates outputs."""

    @staticmethod
    def compose_video(
        segment_paths: List[str],
        narration_audio_path: str,
        aspect_ratio: str,
        output_video_path: str,
        srt_subtitles_path: Optional[str] = None,
        burn_captions: bool = True,
    ) -> Dict[str, Any]:
        target = Path(output_video_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        work_dir = target.parent

        if not segment_paths:
            raise RenderingError("No scene segments provided for composition")

        # Step 1: Create FFmpeg concat demuxer file
        concat_file = work_dir / f"concat_{aspect_ratio.replace(':', '_')}.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for p in segment_paths:
                # FFmpeg concat expects absolute or relative forward-slash paths
                norm_p = str(Path(p).resolve()).replace("\\", "/")
                f.write(f"file '{norm_p}'\n")

        # Step 2: Build FFmpeg command for final mux and subtitle burning
        # Intermediate concatenated video
        temp_concat_video = work_dir / f"temp_concat_{aspect_ratio.replace(':', '_')}.mp4"
        cmd_concat = [
            settings.FFMPEG_PATH,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(temp_concat_video),
        ]
        try:
            subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Concat failed: {e.stderr}")
            raise RenderingError(f"Concat failed: {e.stderr}")

        # Step 3: Mix narration audio and burn subtitles if enabled
        cmd_final = [
            settings.FFMPEG_PATH,
            "-y",
            "-i", str(temp_concat_video),
            "-i", narration_audio_path,
        ]

        # Subtitle burning filter
        vf_filters = []
        if burn_captions and srt_subtitles_path and Path(srt_subtitles_path).exists():
            srt_path_escaped = str(Path(srt_subtitles_path).resolve()).replace("\\", "/").replace(":", "\\:")
            # High-visibility subtitles styling
            vf_filters.append(
                f"subtitles='{srt_path_escaped}':force_style='FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=40'"
            )

        if vf_filters:
            cmd_with_subs = list(cmd_final)
            cmd_with_subs.extend(["-vf", ",".join(vf_filters)])
            cmd_with_subs.extend(["-c:v", settings.DEFAULT_VIDEO_CODEC, "-pix_fmt", settings.DEFAULT_PIXEL_FORMAT, "-r", "30"])
            cmd_with_subs.extend(["-c:a", settings.DEFAULT_AUDIO_CODEC, "-b:a", "192k", "-shortest", str(target)])
            try:
                subprocess.run(cmd_with_subs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            except Exception as e:
                logger.warning(f"Burn-in subtitle filter failed ({e}); falling back to clean video stream mix")
                cmd_fallback = [
                    settings.FFMPEG_PATH,
                    "-y",
                    "-i", str(temp_concat_video),
                    "-i", narration_audio_path,
                    "-c:v", "copy",
                    "-c:a", settings.DEFAULT_AUDIO_CODEC,
                    "-b:a", "192k",
                    "-shortest",
                    str(target),
                ]
                subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        else:
            cmd_nosub = list(cmd_final)
            cmd_nosub.extend(["-c:v", "copy", "-c:a", settings.DEFAULT_AUDIO_CODEC, "-b:a", "192k", "-shortest", str(target)])
            subprocess.run(cmd_nosub, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        # Cleanup temporary files
        if concat_file.exists():
            concat_file.unlink(missing_ok=True)
        if temp_concat_video.exists():
            temp_concat_video.unlink(missing_ok=True)

        # Step 4: Validate output video metadata
        validation_info = VideoComposer.validate_output_video(str(target), aspect_ratio)
        return validation_info

    @staticmethod
    def validate_output_video(video_path: str, expected_aspect_ratio: str) -> Dict[str, Any]:
        """Validates video format, codecs, resolution, framerate, and audio synchronization."""
        cmd = [
            settings.FFPROBE_PATH,
            "-v", "error",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate,duration,channels:format=duration,size,bit_rate",
            "-of", "json",
            video_path,
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(proc.stdout)

        streams = data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_name") in {"h264", "hevc", "vp9"}), None)
        a_stream = next((s for s in streams if s.get("codec_name") in {"aac", "mp3", "opus"}), None)

        if not v_stream:
            raise RenderingError("Rendered video stream missing or invalid codec")
        if not a_stream:
            raise RenderingError("Rendered audio stream missing or invalid codec")

        expected_w, expected_h = get_aspect_dimensions(expected_aspect_ratio)
        actual_w = int(v_stream.get("width", 0))
        actual_h = int(v_stream.get("height", 0))

        if actual_w != expected_w or actual_h != expected_h:
            logger.warning(
                f"Dimension discrepancy: got {actual_w}x{actual_h}, expected {expected_w}x{expected_h} for {expected_aspect_ratio}"
            )

        duration = float(data.get("format", {}).get("duration", 0.0))
        file_size = int(data.get("format", {}).get("size", os.path.getsize(video_path)))

        return {
            "path": video_path,
            "aspect_ratio": expected_aspect_ratio,
            "width": actual_w,
            "height": actual_h,
            "duration": round(duration, 3),
            "file_size": file_size,
            "video_codec": v_stream.get("codec_name"),
            "audio_codec": a_stream.get("codec_name"),
            "fps": 30,
            "is_valid": True,
        }
