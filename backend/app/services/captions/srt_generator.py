from pathlib import Path
from typing import Any, Dict, List


def format_srt_timestamp(seconds: float) -> str:
    """Converts seconds float (e.g. 12.345) to SRT timestamp: HH:MM:SS,mmm"""
    ms = int(round((seconds - int(seconds)) * 1000))
    total_seconds = int(seconds)
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d},{ms:03d}"


class SRTGenerator:
    """Generates standard compliant SRT subtitle files from scenes or transcript segments."""

    @staticmethod
    def generate_srt_from_scenes(scenes: List[Dict[str, Any]], output_path: str) -> str:
        srt_lines = []
        counter = 1

        for sc in scenes:
            text = sc.get("text", "").strip()
            if not text:
                continue

            start_str = format_srt_timestamp(sc["start_time"])
            end_str = format_srt_timestamp(sc["end_time"])

            srt_lines.append(str(counter))
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(text)
            srt_lines.append("")
            counter += 1

        content = "\n".join(srt_lines)
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

        return str(target)
