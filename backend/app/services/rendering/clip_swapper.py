
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from backend.app.core.errors import (
    FootageNotFoundError,
    JobNotFoundError,
    ValidationError,
)
from backend.app.core.logging import logger
from backend.app.db.session import SessionLocal
from backend.app.models.job import Job, SceneModel
from backend.app.services.footage.resilient_fetcher import ResilientFootageFetcher
from backend.app.services.rendering.scene_renderer import SceneRenderer
from backend.app.services.rendering.video_composer import VideoComposer
from backend.app.utils.storage import get_storage_service


class ClipSwapper:
    """
    Implements Advanced Level Feature 16.B:

    Fast partial rerendering for clip swapping without retranscribing
    audio or rerendering unaffected scenes.

    Production uses configured footage providers.
    Mock footage is available only when explicitly enabled for testing.
    """

    @staticmethod
    async def swap_scene_clip(
        job_id: str,
        scene_id: str,
        new_clip_id: Optional[str] = None,
        new_visual_hint: Optional[str] = None,
        is_mock: bool = False,
    ) -> Dict[str, Any]:

        start_time = time.time()
        work_dir = Path(f"./storage/jobs/{job_id}").resolve()
        storage = get_storage_service()

        # --------------------------------------------------
        # 1. Load job and scene
        # --------------------------------------------------

        db = SessionLocal()

        try:
            job = db.query(Job).filter(
                Job.id == job_id
            ).first()

            if not job:
                raise JobNotFoundError(job_id)

            scene = db.query(SceneModel).filter(
                SceneModel.job_id == job_id,
                SceneModel.id == scene_id,
            ).first()

            if not scene:
                if str(scene_id).isdigit():
                    scene = db.query(SceneModel).filter(
                        SceneModel.job_id == job_id,
                        SceneModel.scene_index == int(scene_id),
                    ).first()

                elif str(scene_id).startswith("scene_"):
                    try:
                        idx = int(scene_id.split("_")[1]) - 1

                        scene = db.query(SceneModel).filter(
                            SceneModel.job_id == job_id,
                            SceneModel.scene_index == idx,
                        ).first()

                    except (ValueError, IndexError):
                        scene = None

                if not scene:
                    scene = db.query(SceneModel).filter(
                        SceneModel.job_id == job_id,
                        SceneModel.id.like(f"%{scene_id}%"),
                    ).first()

            if not scene:
                raise ValidationError(
                    f"Scene '{scene_id}' not found in job {job_id}"
                )

            before_clip = scene.selected_clip_id
            scene_index = scene.scene_index
            scene_duration = scene.duration
            current_provider_asset_id = scene.provider_asset_id

            aspect_ratios = job.aspect_ratios or ["16:9"]

            captions_config = dict(job.captions_config or {})
            burn_captions = captions_config.get("burn_in", True)

            all_scenes = db.query(SceneModel).filter(
                SceneModel.job_id == job_id
            ).order_by(
                SceneModel.scene_index
            ).all()

            scene_search_query = scene.search_query
            scene_db_id = scene.id

        finally:
            db.close()

        # --------------------------------------------------
        # 2. Find replacement footage
        # --------------------------------------------------

        fetcher = ResilientFootageFetcher(use_mock=is_mock)

        query = (
            new_visual_hint.strip()
            if new_visual_hint and new_visual_hint.strip()
            else scene_search_query
        )

        if not query:
            raise ValidationError(
                "A visual hint or existing scene search query is required."
            )

        candidates, providers_tried = (
            await fetcher.get_candidates_for_query(
                query,
                limit=10,
            )
        )

        # If a particular clip ID was requested, find that exact candidate.
        if new_clip_id:
            new_cand = next(
                (
                    candidate
                    for candidate in candidates
                    if candidate.provider_asset_id == new_clip_id
                ),
                None,
            )

            if not new_cand:
                raise FootageNotFoundError(
                    f"Requested replacement clip '{new_clip_id}' "
                    "was not found among eligible candidates."
                )

        else:
            # Prefer a candidate different from the current clip.
            new_cand = next(
                (
                    candidate
                    for candidate in candidates
                    if candidate.provider_asset_id
                    != current_provider_asset_id
                ),
                None,
            )

            # If only one candidate exists, allow it.
            if not new_cand and candidates:
                new_cand = candidates[0]

        if not new_cand:
            raise FootageNotFoundError(
                f"No eligible replacement footage found for '{query}'. "
                f"Providers tried: {providers_tried}. "
                "Try another visual hint or configure a footage provider. "
                "Synthetic fallback footage is disabled."
            )

        # --------------------------------------------------
        # 3. Download replacement footage
        # --------------------------------------------------

        work_dir.mkdir(parents=True, exist_ok=True)

        safe_asset_id = "".join(
            char if char.isalnum() or char in "-_" else "_"
            for char in new_cand.provider_asset_id
        )

        raw_clip_filename = (
            f"raw_swap_{scene_index + 1}_{safe_asset_id}.mp4"
        )

        raw_clip_path = str(work_dir / raw_clip_filename)

        await fetcher.download_selected_candidate(
            new_cand,
            raw_clip_path,
        )

        if not Path(raw_clip_path).exists():
            raise FootageNotFoundError(
                "Replacement footage download did not produce a file."
            )

        # --------------------------------------------------
        # 4. Rerender only the affected scene
        # --------------------------------------------------

        updated_aspect_outputs = {}

        for ratio in aspect_ratios:
            ratio_clean = ratio.replace(":", "_")

            seg_filename = (
                f"segment_s{scene_index + 1}_{ratio_clean}.mp4"
            )

            seg_path = str(work_dir / seg_filename)

            SceneRenderer.render_scene_segment(
                raw_clip_path=raw_clip_path,
                duration=scene_duration,
                aspect_ratio=ratio,
                output_path=seg_path,
            )

            if not Path(seg_path).exists():
                raise RuntimeError(
                    f"Scene rendering failed for aspect ratio {ratio}"
                )

            updated_aspect_outputs[ratio] = seg_filename

        # --------------------------------------------------
        # 5. Recompose final videos
        # --------------------------------------------------

        narration_path = str(work_dir / "narration.wav")
        srt_path = str(work_dir / "captions.srt")

        if not Path(narration_path).exists():
            raise FileNotFoundError(
                f"Narration audio not found: {narration_path}"
            )

        new_video_outputs = {}

        for ratio in aspect_ratios:
            ratio_clean = ratio.replace(":", "_")
            ordered_segments = []

            for sc in all_scenes:
                if sc.id == scene_db_id:
                    segment_filename = updated_aspect_outputs[ratio]
                else:
                    segment_filename = (
                        (sc.aspect_ratio_outputs or {}).get(
                            ratio,
                            f"segment_s{sc.scene_index + 1}_{ratio_clean}.mp4",
                        )
                    )

                segment_path = work_dir / segment_filename

                if not segment_path.exists():
                    raise FileNotFoundError(
                        f"Required cached scene segment missing: "
                        f"{segment_path}"
                    )

                ordered_segments.append(str(segment_path))

            final_video_name = (
                f"brollforge_{job_id}_{ratio_clean}.mp4"
            )

            final_video_path = str(
                work_dir / final_video_name
            )

            val_info = VideoComposer.compose_video(
                segment_paths=ordered_segments,
                narration_audio_path=narration_path,
                aspect_ratio=ratio,
                output_video_path=final_video_path,
                srt_subtitles_path=(
                    srt_path if Path(srt_path).exists() else None
                ),
                burn_captions=burn_captions,
            )

            video_url = storage.save_file(
                final_video_path,
                f"jobs/{job_id}/{final_video_name}",
            )

            new_video_outputs[ratio] = {
                "url": video_url,
                "width": val_info["width"],
                "height": val_info["height"],
                "duration": val_info["duration"],
                "file_size": val_info["file_size"],
                "aspect_ratio": ratio,
            }

        # --------------------------------------------------
        # 6. Update timeline
        # --------------------------------------------------

        timeline_file = work_dir / "timeline.json"
        manifest_file = work_dir / "manifest.json"

        tl_updated = None
        mf_updated = None

        if timeline_file.exists():
            with open(
                timeline_file,
                "r",
                encoding="utf-8",
            ) as file:
                tl_updated = json.load(file)

            for timeline_scene in tl_updated.get("scenes", []):
                if (
                    timeline_scene.get("scene_id") == scene_db_id
                    or timeline_scene.get("scene_index") == scene_index
                ):
                    timeline_scene.update({
                        "selected_clip": raw_clip_filename,
                        "provider": new_cand.provider,
                        "provider_asset_id": new_cand.provider_asset_id,
                        "source_url": new_cand.source_url,
                        "licence_name": new_cand.licence_name,
                        "licence_url": new_cand.licence_url,
                        "attribution": new_cand.attribution,
                        "creator": new_cand.creator,
                        "aspect_ratio_outputs": updated_aspect_outputs,
                        "selection_reason": (
                            "Replaced via clip swapping API. "
                            f"Visual hint: '{query}'"
                        ),
                    })

            with open(
                timeline_file,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(tl_updated, file, indent=2)

            storage.save_file(
                str(timeline_file),
                f"jobs/{job_id}/timeline.json",
            )

        # --------------------------------------------------
        # 7. Update manifest
        # --------------------------------------------------

        if manifest_file.exists():
            with open(
                manifest_file,
                "r",
                encoding="utf-8",
            ) as file:
                mf_updated = json.load(file)

            mf_updated["output_files"] = {
                "videos": new_video_outputs,
            }

            provider_licences = mf_updated.get(
                "provider_licences",
                [],
            )

            provider_licences.append({
                "provider": new_cand.provider,
                "provider_asset_id": new_cand.provider_asset_id,
                "source_url": new_cand.source_url,
                "licence_name": new_cand.licence_name,
                "licence_url": new_cand.licence_url,
                "attribution": new_cand.attribution,
                "creator": new_cand.creator,
                "is_ai_generated": new_cand.is_ai_generated,
            })

            mf_updated["provider_licences"] = provider_licences

            with open(
                manifest_file,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(mf_updated, file, indent=2)

            storage.save_file(
                str(manifest_file),
                f"jobs/{job_id}/manifest.json",
            )

        # --------------------------------------------------
        # 8. Update database
        # --------------------------------------------------

        swap_duration = round(
            time.time() - start_time,
            3,
        )

        db = SessionLocal()

        try:
            target_scene = db.query(SceneModel).filter(
                SceneModel.id == scene_db_id
            ).first()

            if target_scene:
                target_scene.selected_clip_id = raw_clip_filename
                target_scene.provider = new_cand.provider
                target_scene.provider_asset_id = new_cand.provider_asset_id
                target_scene.source_url = new_cand.source_url
                target_scene.licence_name = new_cand.licence_name
                target_scene.licence_url = new_cand.licence_url
                target_scene.attribution = new_cand.attribution
                target_scene.creator = new_cand.creator
                target_scene.aspect_ratio_outputs = updated_aspect_outputs

                target_scene.selection_reason = (
                    "Replaced via clip swapping API. "
                    f"New visual hint: '{query}'"
                )

            job_rec = db.query(Job).filter(
                Job.id == job_id
            ).first()

            if job_rec:
                result_links = dict(job_rec.result_links or {})
                result_links["videos"] = new_video_outputs
                job_rec.result_links = result_links

                if tl_updated is not None:
                    job_rec.timeline_data = tl_updated

                if mf_updated is not None:
                    job_rec.manifest_data = mf_updated

            db.commit()

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

        logger.info(
            f"Clip swapped successfully for scene {scene_id} "
            f"in {swap_duration}s"
        )

        return {
            "job_id": job_id,
            "scene_id": scene_id,
            "swap_time_seconds": swap_duration,
            "before_clip": before_clip,
            "after_clip": raw_clip_filename,
            "new_provider": new_cand.provider,
            "new_license": new_cand.licence_name,
            "result_links": {
                "videos": new_video_outputs,
            },
        }
