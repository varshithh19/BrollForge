from typing import Dict, Tuple

ASPECT_CONFIGS: Dict[str, Dict[str, int]] = {
    "16:9": {"width": 1920, "height": 1080},
    "9:16": {"width": 1080, "height": 1920},
    "1:1": {"width": 1080, "height": 1080},
}


def get_aspect_dimensions(aspect_ratio: str) -> Tuple[int, int]:
    cfg = ASPECT_CONFIGS.get(aspect_ratio, ASPECT_CONFIGS["16:9"])
    return cfg["width"], cfg["height"]


def build_aspect_filter(aspect_ratio: str) -> str:
    """
    Constructs an FFmpeg video filter graph that scales and crops to target aspect ratio
    without distortion, forcing square pixel aspect ratio (SAR=1).
    """
    width, height = get_aspect_dimensions(aspect_ratio)
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"setsar=1,"
        f"fps=30"
    )
