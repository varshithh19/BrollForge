
import os
import uuid
from pathlib import Path

import pytest

from backend.app.db.session import SessionLocal
from backend.app.models.job import Job
from backend.app.services.pipeline import VideoEnginePipeline
from backend.app.services.rendering.clip_swapper import ClipSwapper
from backend.app.services.rendering.video_composer import VideoComposer


@pytest.mark.asyncio
async def test_end_to_end_video_generation_pipeline():
    job_id = f"e2e-test-{uuid.uuid4().hex[:8]}"

    # Insert test job in DB
    db = SessionLocal()

    job = Job(
        id=job_id,
        status="queued",
        progress=0,
        stage="queued",
        input_type="script",
        input_payload={
            "script": (
                "Trust is earned slowly. Sales grew 40% in 2025 "
                "as modern teams embraced cloud computing."
            ),
            "voice": "en-IN-female",
        },
        aspect_ratios=["16:9", "9:16", "1:1"],
        style="bright, modern, real-world footage",
        avoid=["people's faces", "alcohol"],
        captions_config={
            "burn_in": True,
            "srt": True,
        },
    )

    db.add(job)
    db.commit()
    db.close()

    # Execute pipeline using mock footage for testing
    pipeline = VideoEnginePipeline(
        job_id=job_id,
        is_mock=True,
    )

    result_links = await pipeline.run()

    # 1. Verify result links
    assert "videos" in result_links
    assert "16:9" in result_links["videos"]
    assert "9:16" in result_links["videos"]
    assert "1:1" in result_links["videos"]

    assert "timeline" in result_links
    assert "manifest" in result_links
    assert "captions_srt" in result_links

    # 2. Verify all 3 video files exist and validate using ffprobe
    job_dir = Path(f"./storage/jobs/{job_id}")

    for ratio in ["16:9", "9:16", "1:1"]:
        ratio_clean = ratio.replace(":", "_")

        video_path = (
            job_dir
            / f"brollforge_{job_id}_{ratio_clean}.mp4"
        )

        assert video_path.exists(), (
            f"Video file {video_path} does not exist"
        )

        probe_info = VideoComposer.validate_output_video(
            str(video_path),
            ratio,
        )

        assert probe_info["is_valid"] is True
        assert probe_info["video_codec"] == "h264"
        assert probe_info["audio_codec"] == "aac"
        assert probe_info["fps"] == 30

        if ratio == "16:9":
            assert (
                probe_info["width"] == 1920
                and probe_info["height"] == 1080
            )

        elif ratio == "9:16":
            assert (
                probe_info["width"] == 1080
                and probe_info["height"] == 1920
            )

        elif ratio == "1:1":
            assert (
                probe_info["width"] == 1080
                and probe_info["height"] == 1080
            )

    # 3. Verify timeline, manifest, and captions exist
    assert (job_dir / "timeline.json").exists()
    assert (job_dir / "manifest.json").exists()
    assert (job_dir / "captions.srt").exists()

    # 4. Verify DB job status
    db = SessionLocal()

    try:
        completed_job = (
            db.query(Job)
            .filter(Job.id == job_id)
            .first()
        )

        assert completed_job is not None
        assert completed_job.status == "succeeded"
        assert completed_job.progress == 100
        assert len(completed_job.scenes) >= 1

        scene_ids = [scene.id for scene in completed_job.scenes]
        first_scene_id = scene_ids[0]

    finally:
        db.close()

    # 5. Test advanced feature: clip swapping with partial rerender
    # Explicitly enable mock footage for this test only.
    swap_res = await ClipSwapper.swap_scene_clip(
        job_id=job_id,
        scene_id=first_scene_id,
        new_visual_hint="modern software engineering workstation",
        is_mock=True,
    )

    assert swap_res["job_id"] == job_id
    assert swap_res["swap_time_seconds"] > 0
    assert "result_links" in swap_res
