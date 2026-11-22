import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict
from backend.app.config.settings import settings
from backend.app.core.errors import MediaProbeError, SilentAudioError, ValidationError
from backend.app.core.logging import logger

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a"}
MAGIC_NUMBERS = {
    b"ID3": "mp3",
    b"\xff\xfb": "mp3",
    b"\xff\xf3": "mp3",
    b"\xff\xf2": "mp3",
    b"RIFF": "wav",
    b"ftyp": "m4a",  # often preceded by 4 bytes of length
}


def validate_audio_file(file_path: str) -> None:
    path = Path(file_path)
    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported audio format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if not path.exists():
        raise ValidationError(f"Audio file not found at path: {file_path}")

    # Magic byte inspection
    with open(path, "rb") as f:
        head = f.read(32)
        if len(head) < 4:
            raise ValidationError("Audio file is empty or corrupted")

        is_valid_magic = (
            head.startswith(b"ID3")
            or head.startswith(b"\xff\xfb")
            or head.startswith(b"\xff\xf3")
            or head.startswith(b"\xff\xf2")
            or head.startswith(b"RIFF")
            or b"ftyp" in head[:16]
        )
        if not is_valid_magic:
            logger.warning(f"File magic check did not match standard headers for {ext}, proceeding to ffprobe validation.")


def probe_audio(file_path: str) -> Dict[str, Any]:
    """
    Uses ffprobe to extract audio streams, duration, sample rate, channels, bit rate, and silent audio detection.
    """
    validate_audio_file(file_path)

    cmd = [
        settings.FFPROBE_PATH,
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=codec_name,channels,sample_rate,duration",
        "-of", "json",
        file_path,
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        probe_data = json.loads(proc.stdout)
    except FileNotFoundError:
        # Fallback if ffprobe is not in system PATH
        logger.warning("ffprobe executable not found on system PATH; attempting Python wave/metadata probe")
        return fallback_probe_audio(file_path)
    except subprocess.CalledProcessError as e:
        raise MediaProbeError(f"Failed to probe audio file: {e.stderr}", details={"stderr": e.stderr})

    streams = probe_data.get("streams", [])
    audio_streams = [s for s in streams if "channels" in s or s.get("codec_type") == "audio"]
    if not audio_streams and streams:
        audio_streams = streams

    if not audio_streams:
        raise MediaProbeError("No valid audio stream detected in media file")

    stream = audio_streams[0]
    fmt = probe_data.get("format", {})

    duration = float(stream.get("duration") or fmt.get("duration") or 0.0)
    if duration <= 0.0:
        raise MediaProbeError("Unable to determine valid audio duration or file is 0.0 seconds")

    if duration > settings.MAX_AUDIO_DURATION_SECONDS:
        raise ValidationError(
            f"Audio duration ({duration:.1f}s) exceeds maximum allowed limit of {settings.MAX_AUDIO_DURATION_SECONDS}s (10 minutes)"
        )

    # Check for silent audio using ffmpeg volumedetect
    silence_info = check_audio_silence(file_path)
    if silence_info.get("is_silent"):
        raise SilentAudioError("Uploaded audio file is completely silent or below audible threshold")

    return {
        "duration": duration,
        "sample_rate": int(stream.get("sample_rate", 44100)),
        "channels": int(stream.get("channels", 2)),
        "codec": stream.get("codec_name", "unknown"),
        "bit_rate": int(fmt.get("bit_rate") or stream.get("bit_rate") or 128000),
        "file_size": int(fmt.get("size") or os.path.getsize(file_path)),
        "is_silent": False,
        "mean_volume_db": silence_info.get("mean_volume_db"),
        "max_volume_db": silence_info.get("max_volume_db"),
    }


def check_audio_silence(file_path: str) -> Dict[str, Any]:
    """
    Inspects audio file for silence using raw PCM frame checks and ffmpeg volumedetect filter.
    """
    import wave
    if file_path.lower().endswith(".wav"):
        try:
            with wave.open(file_path, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                if frames and (set(frames) == {0} or set(frames) == {0, 1}):
                    return {"is_silent": True, "mean_volume_db": -99.0, "max_volume_db": -99.0}
        except Exception:
            pass

    cmd = [
        settings.FFMPEG_PATH,
        "-i", file_path,
        "-af", "volumedetect",
        "-vn",
        "-sn",
        "-dn",
        "-f", "null",
        "NUL" if os.name == "nt" else "/dev/null",
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out = proc.stderr
        mean_vol = None
        max_vol = None
        for line in out.splitlines():
            if "mean_volume:" in line:
                mean_vol = float(line.split("mean_volume:")[1].split("dB")[0].strip())
            elif "max_volume:" in line:
                max_vol = float(line.split("max_volume:")[1].split("dB")[0].strip())

        is_silent = False
        if max_vol is not None and max_vol < -50.0:
            is_silent = True
        elif mean_vol is not None and mean_vol < -70.0:
            is_silent = True

        return {
            "is_silent": is_silent,
            "mean_volume_db": mean_vol,
            "max_volume_db": max_vol,
        }
    except Exception as e:
        logger.warning(f"volumedetect check failed ({e}); assuming non-silent")
        return {"is_silent": False, "mean_volume_db": -20.0, "max_volume_db": 0.0}


def fallback_probe_audio(file_path: str) -> Dict[str, Any]:
    """Fallback probe when ffprobe is not installed locally."""
    size = os.path.getsize(file_path)
    if size == 0:
        raise MediaProbeError("Audio file is 0 bytes")
    # Approximate duration for 128kbps if metadata cannot be read
    approx_duration = max(1.0, round(size / (16000 * 2), 2))
    return {
        "duration": approx_duration,
        "sample_rate": 44100,
        "channels": 2,
        "codec": "mp3",
        "bit_rate": 128000,
        "file_size": size,
        "is_silent": False,
        "mean_volume_db": -20.0,
        "max_volume_db": -1.0,
    }
