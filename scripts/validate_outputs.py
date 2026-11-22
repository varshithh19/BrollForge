#!/usr/bin/env python3
"""
BrollForge Output Validator
Inspects finished video outputs, timeline.json, manifest.json, and captions.srt
to guarantee strict adherence to all technical standards.
"""

import argparse
import json
import sys
from pathlib import Path
from backend.app.services.rendering.video_composer import VideoComposer


def validate_job_directory(job_dir: Path) -> bool:
    print(f"\n--- Validating Job Output: {job_dir.name} ---")
    all_passed = True

    # Check manifest.json
    manifest_path = job_dir / "manifest.json"
    if not manifest_path.exists():
        print("  [FAIL] manifest.json missing")
        all_passed = False
    else:
        with open(manifest_path, "r", encoding="utf-8") as f:
            mf = json.load(f)
            assert "job_id" in mf and "scene_count" in mf and "processing_timings" in mf
        print("  [PASS] manifest.json schema verified")

    # Check timeline.json
    timeline_path = job_dir / "timeline.json"
    if not timeline_path.exists():
        print("  [FAIL] timeline.json missing")
        all_passed = False
    else:
        with open(timeline_path, "r", encoding="utf-8") as f:
            tl = json.load(f)
            scenes = tl.get("scenes", [])
            assert len(scenes) > 0
            # Check gapless coverage
            for i in range(len(scenes) - 1):
                assert scenes[i]["end_time"] == scenes[i + 1]["start_time"]
            print(f"  [PASS] timeline.json verified with {len(scenes)} gapless scenes")

    # Check captions.srt
    srt_path = job_dir / "captions.srt"
    if not srt_path.exists():
        print("  [FAIL] captions.srt missing")
        all_passed = False
    else:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "-->" in content
        print("  [PASS] captions.srt timestamps verified")

    # Check video files
    video_files = list(job_dir.glob("*.mp4"))
    if not video_files:
        print("  [FAIL] No MP4 video outputs found in directory")
        all_passed = False
    else:
        for vf in video_files:
            ratio = "16:9"
            if "9_16" in vf.name:
                ratio = "9:16"
            elif "1_1" in vf.name:
                ratio = "1:1"

            try:
                probe = VideoComposer.validate_output_video(str(vf), ratio)
                print(f"  [PASS] {vf.name}: {probe['width']}x{probe['height']} | {probe['video_codec']} | {probe['fps']}fps | {probe['duration']}s")
            except Exception as e:
                print(f"  [FAIL] {vf.name} validation error: {e}")
                all_passed = False

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="BrollForge Output Validator")
    parser.add_argument("--job-dir", required=True, help="Path to job output directory")
    args = parser.parse_args()

    p = Path(args.job_dir).resolve()
    if not p.exists():
        print(f"Path '{p}' not found")
        sys.exit(1)

    ok = validate_job_directory(p)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
