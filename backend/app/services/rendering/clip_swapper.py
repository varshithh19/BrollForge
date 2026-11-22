import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from backend.app.config.settings import settings
from backend.app.core.errors import JobNotFoundError, ValidationError
from backend.app.core.logging import logger
from backend.app.db.session import SessionLocal
from backend.app.models.job import Job, SceneModel
from backend.app.services.footage.resilient_fetcher import ResilientFootageFetcher
from backend.app.services.manifests.generator import ManifestGenerator
from backend.app.services.rendering.scene_renderer import SceneRenderer
from backend.app.services.rendering.video_composer import VideoComposer
from backend.app.utils.storage import get_storage_service


class ClipSwapper:
    """
    Implements Advanced Level Feature 16.B:
    Fast partial rerendering for clip swapping without retranscribing audio or rerendering unaffected scenes.
    """

    @staticmethod
    async def swap_scene_clip(
        job_id: str,
        scene_id: str,
        new_clip_id: Optional[str] = None,
        new_visual_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        work_dir = Path(f"./storage/jobs/{job_id}").resolve()
        storage = get_storage_service()

        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise JobNotFoundError(job_id)

            scene = db.query(SceneModel).filter(SceneModel.job_id == job_id, SceneModel.id == scene_id).first()
            if not scene:
                if str(scene_id).isdigit():
                    scene = db.query(SceneModel).filter(SceneModel.job_id == job_id, SceneModel.scene_index == int(scene_id)).first()
                elif str(scene_id).startswith("scene_"):
                    try:
                        idx = int(scene_id.split("_")[1]) - 1
                        scene = db.query(SceneModel).filter(SceneModel.job_id == job_id, SceneModel.scene_index == idx).first()
                    except Exception:
                        pass
                if not scene:
                    scene = db.query(SceneModel).filter(
                        SceneModel.job_id == job_id,
                        (SceneModel.id.like(f"%{scene_id}%"))
                    ).first()
            if not scene:
                raise ValidationError(f"Scene '{scene_id}' not found in job {job_id}")

            before_clip = scene.selected_clip_id
            aspect_ratios = job.aspect_ratios or ["16:9"]
            all_scenes = db.query(SceneModel).filter(SceneModel.job_id == job_id).order_by(SceneModel.scene_index).all()
        finally:
            db.close()

        fetcher = ResilientFootageFetcher()
        query = new_visual_hint or scene.search_query
        candidates, _ = await fetcher.get_candidates_for_query(query, limit=5)

        # Pick candidate that differs from current
        new_cand = None
        for c in candidates:
            if c.provider_asset_id != scene.provider_asset_id:
                new_cand = c
                break
        if not new_cand and candidates:
            new_cand = candidates[0]

        if not new_cand:
            # Fallback to local pack
            cands = await fetcher.local_pack.search(query, limit=2)
            new_cand = cands[0]

        # Download replacement clip
        raw_clip_filename = f"raw_swap_{scene.scene_index + 1}_{new_cand.provider_asset_id}.mp4"
        raw_clip_path = str(work_dir / raw_clip_filename)
        await fetcher.download_selected_candidate(new_cand, raw_clip_path)

        # Rerender ONLY the affected scene segments for each aspect ratio
        updated_aspect_outputs = dict(scene.aspect_ratio_outputs or {})
        for ratio in aspect_ratios:
            ratio_clean = ratio.replace(":", "_")
            seg_filename = f"segment_s{scene.scene_index + 1}_{ratio_clean}.mp4"
            seg_path = str(work_dir / seg_filename)
            SceneRenderer.render_scene_segment(
                raw_clip_path=raw_clip_path,
                duration=scene.duration,
                aspect_ratio=ratio,
                output_path=seg_path,
            )
            updated_aspect_outputs[ratio] = seg_filename

        # Recompose final videos from unchanged cached segments + the newly rerendered segment
        srt_path = str(work_dir / "captions.srt")
        narration_path = str(work_dir / "narration.wav")
        new_result_links = dict(job.result_links or {})
        new_result_links["videos"] = {}

        for ratio in aspect_ratios:
            ratio_clean = ratio.replace(":", "_")
            # Collect ordered segment paths across all scenes
            ordered_segments = []
            for sc in all_scenes:
                if sc.id == scene.id:
                    s_file = updated_aspect_outputs[ratio]
                else:
                    s_file = (sc.aspect_ratio_outputs or {}).get(ratio, f"segment_s{sc.scene_index + 1}_{ratio_clean}.mp4")
                ordered_segments.append(str(work_dir / s_file))

            final_video_name = f"brollforge_{job_id}_{ratio_clean}.mp4"
            final_video_path = str(work_dir / final_video_name)

            val_info = VideoComposer.compose_video(
                segment_paths=ordered_segments,
                narration_audio_path=narration_path,
                aspect_ratio=ratio,
                output_video_path=final_video_path,
                srt_subtitles_path=srt_path,
                burn_captions=job.captions_config.get("burn_in", True),
            )
            video_url = storage.save_file(final_video_path, f"jobs/{job_id}/{final_video_name}")
            new_result_links["videos"][ratio] = {
                "url": video_url,
                "width": val_info["width"],
                "height": val_info["height"],
                "duration": val_info["duration"],
                "file_size": val_info["file_size"],
                "aspect_ratio": ratio,
            }

        swap_duration = round(time.time() - start_time, 3)

        # Update Database
        db = SessionLocal()
        try:
            target_scene = db.query(SceneModel).filter(SceneModel.id == scene.id).first()
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
                target_scene.selection_reason = f"Replaced via clip swapping API. New visual hint: '{new_visual_hint}'"

            # Update timeline.json and manifest.json
            tl_updated = None
            timeline_file = work_dir / "timeline.json"
            if timeline_file.exists():
                with open(timeline_file, "r", encoding="utf-8") as f:
                    tl_updated = json.load(f)
                for sc in tl_updated.get("scenes", []):
                    if sc.get("scene_id") == scene.id or sc.get("scene_index") == scene.scene_index:
                        sc["selected_clip"] = raw_clip_filename
                        sc["provider"] = new_cand.provider
                        sc["provider_asset_id"] = new_cand.provider_asset_id
                        sc["source_url"] = new_cand.source_url
                        sc["licence_name"] = new_cand.licence_name
                        sc["licence_url"] = new_cand.licence_url
                        sc["attribution"] = new_cand.attribution
                        sc["creator"] = new_cand.creator
                        sc["aspect_ratio_outputs"] = updated_aspect_outputs
                        sc["selection_reason"] = f"Replaced via clip swapping API. Visual hint: '{new_visual_hint}'"
                with open(timeline_file, "w", encoding="utf-8") as f:
                    json.dump(tl_updated, f, indent=2)
                storage.save_file(str(timeline_file), f"jobs/{job_id}/timeline.json")

            mf_updated = None
            manifest_file = work_dir / "manifest.json"
            if manifest_file.exists():
                with open(manifest_file, "r", encoding="utf-8") as f:
                    mf_updated = json.load(f)
                mf_updated["output_files"] = new_result_links
                prov_list = mf_updated.get("provider_licences", [])
                prov_list.append({
                    "provider": new_cand.provider,
                    "licence_name": new_cand.licence_name,
                    "licence_url": new_cand.licence_url,
                    "attribution": new_cand.attribution,
                    "is_ai_generated": new_cand.is_ai_generated,
                })
                mf_updated["provider_licences"] = prov_list
                with open(manifest_file, "w", encoding="utf-8") as f:
                    json.dump(mf_updated, f, indent=2)
                storage.save_file(str(manifest_file), f"jobs/{job_id}/manifest.json")

            job_rec = db.query(Job).filter(Job.id == job_id).first()
            if job_rec:
                job_rec.result_links = new_result_links
                if tl_updated:
                    job_rec.timeline_data = tl_updated
                if mf_updated:
                    job_rec.manifest_data = mf_updated
            db.commit()
        finally:
            db.close()

        logger.info(f"Clip swapped successfully for scene {scene_id} in {swap_duration}s")
        return {
            "job_id": job_id,
            "scene_id": scene_id,
            "swap_time_seconds": swap_duration,
            "before_clip": before_clip,
            "after_clip": raw_clip_filename,
            "new_provider": new_cand.provider,
            "new_license": new_cand.licence_name,
            "result_links": new_result_links,
        }
