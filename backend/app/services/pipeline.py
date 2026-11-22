import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import httpx
from backend.app.config.settings import settings
from backend.app.core.errors import BrollForgeException, RenderingError, ValidationError
from backend.app.core.logging import logger
from backend.app.db.session import SessionLocal
from backend.app.models.job import Job, SceneModel
from backend.app.services.audio.probe import probe_audio
from backend.app.services.captions.srt_generator import SRTGenerator
from backend.app.services.footage.models import FootageCandidate
from backend.app.services.footage.resilient_fetcher import ResilientFootageFetcher
from backend.app.services.manifests.generator import ManifestGenerator
from backend.app.services.rendering.scene_renderer import SceneRenderer
from backend.app.services.rendering.video_composer import VideoComposer
from backend.app.services.segmentation.meaning_segmenter import MeaningSegmenter
from backend.app.services.semantic_matching.matcher import SemanticFootageMatcher
from backend.app.services.transcription.whisper_adapter import get_transcription_adapter
from backend.app.services.tts.tts_adapter import get_tts_adapter
from backend.app.utils.storage import get_storage_service


class VideoEnginePipeline:
    """
    End-to-end B-roll video generation pipeline orchestrator.
    Executes stages asynchronously, updates job progress, validates outputs,
    and dispatches HMAC-signed webhooks.
    """

    def __init__(self, job_id: str, is_mock: bool = False):
        self.job_id = job_id
        self.is_mock = is_mock
        self.work_dir = Path(f"./storage/jobs/{job_id}").resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.storage = get_storage_service()
        self.segmenter = MeaningSegmenter()
        self.fetcher = ResilientFootageFetcher(use_mock=is_mock)
        self.matcher = SemanticFootageMatcher()

    def update_progress(self, stage: str, progress: int, warnings: Optional[List[str]] = None):
        """Persists stage and progress to database and structured log."""
        logger.info(f"Job {self.job_id} progress: {progress}% - Stage: {stage}")
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == self.job_id).first()
            if job:
                job.stage = stage
                job.progress = progress
                job.status = "running"
                if warnings:
                    job.warnings = list(set((job.warnings or []) + warnings))
                db.commit()
        finally:
            db.close()

    async def run(self) -> Dict[str, Any]:
        start_time = time.time()
        stage_timings: Dict[str, float] = {}
        warnings: List[str] = []
        fallbacks_used: List[str] = []

        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == self.job_id).first()
            if not job:
                raise ValidationError(f"Job {self.job_id} not found in database")

            input_type = job.input_type
            payload = job.input_payload or {}
            aspect_ratios = job.aspect_ratios or ["16:9"]
            style = job.style or "bright, modern, real-world footage"
            avoid_list = job.avoid or []
            captions_cfg = job.captions_config or {"burn_in": True, "srt": True}
            callback_url = job.callback_url
        finally:
            db.close()

        # ---------------------------------------------------------
        # STAGE 1: Audio Ingestion or TTS Generation (10%)
        # ---------------------------------------------------------
        s1_start = time.time()
        self.update_progress("audio_preparation", 10)
        audio_path = str(self.work_dir / "narration.wav")
        tts_info = None

        if input_type == "script":
            script_text = payload.get("script", "").strip()
            if not script_text:
                raise ValidationError("Script text is empty")
            voice = payload.get("voice", "en-IN-female")
            tts = get_tts_adapter()
            tts_info = await tts.generate_speech(script_text, audio_path, voice=voice)
        elif input_type == "audio_url":
            audio_url = payload.get("audio_url")
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(audio_url)
                resp.raise_for_status()
                with open(audio_path, "wb") as f:
                    f.write(resp.content)
        elif input_type == "audio_upload":
            raw_path = payload.get("file_path")
            if not raw_path or not Path(raw_path).exists():
                raise ValidationError("Uploaded audio file path invalid or missing")
            audio_path = raw_path

        stage_timings["audio_preparation"] = round(time.time() - s1_start, 3)

        # ---------------------------------------------------------
        # STAGE 2: Media Probing & Validation (20%)
        # ---------------------------------------------------------
        s2_start = time.time()
        self.update_progress("media_probing", 20)
        audio_probe = probe_audio(audio_path)
        total_audio_duration = audio_probe["duration"]
        stage_timings["media_probing"] = round(time.time() - s2_start, 3)

        # ---------------------------------------------------------
        # STAGE 3: Audio Transcription (30%)
        # ---------------------------------------------------------
        s3_start = time.time()
        self.update_progress("transcription", 30)
        transcriber = get_transcription_adapter(
            mock=self.is_mock,
            sample_text=payload.get("script") if input_type == "script" else None,
        )
        transcript_data = transcriber.transcribe(audio_path)
        stage_timings["transcription"] = round(time.time() - s3_start, 3)

        # ---------------------------------------------------------
        # STAGE 4: Meaning-Based Scene Segmentation (40%)
        # ---------------------------------------------------------
        s4_start = time.time()
        self.update_progress("scene_segmentation", 40)
        scenes = self.segmenter.segment_transcript(
            transcript_data=transcript_data,
            user_scenes=payload.get("scenes"),
            avoid_rules=avoid_list,
            style=style,
        )
        stage_timings["scene_segmentation"] = round(time.time() - s4_start, 3)

        # ---------------------------------------------------------
        # STAGE 5: Footage Sourcing, Matching & Deduplication (60%)
        # ---------------------------------------------------------
        s5_start = time.time()
        self.update_progress("footage_search_and_matching", 55)
        used_clip_ids: Set[str] = set()
        selected_candidates: List[FootageCandidate] = []
        raw_download_paths: List[str] = []

        for idx, sc in enumerate(scenes):
            query = sc["search_query"]
            candidates, providers_tried = await self.fetcher.get_candidates_for_query(query, limit=8)
            fallbacks_used.extend(providers_tried)

            best_cand, score, reason = self.matcher.rank_and_select(
                scene=sc,
                candidates=candidates,
                used_clip_ids=used_clip_ids,
                avoid_terms=avoid_list,
            )

            if not best_cand:
                # Use local emergency licensed clip
                local_pack = self.fetcher.local_pack
                emergency_cands = await local_pack.search("business modern", limit=5)
                # Find first unused
                for ec in emergency_cands:
                    if ec.provider_asset_id not in used_clip_ids:
                        best_cand = ec
                        score = 3.0
                        reason = "Emergency local licensed fallback selected to guarantee zero duplicate and full scene coverage."
                        warnings.append(f"Scene {idx + 1} used emergency local pack fallback.")
                        break

            # Mark as used to guarantee zero repeat rate
            used_clip_ids.add(f"{best_cand.provider}:{best_cand.provider_asset_id}")
            used_clip_ids.add(best_cand.provider_asset_id)
            selected_candidates.append(best_cand)

            # Download raw footage clip
            raw_clip_filename = f"raw_scene_{idx + 1}_{best_cand.provider_asset_id}.mp4"
            raw_clip_path = str(self.work_dir / raw_clip_filename)
            await self.fetcher.download_selected_candidate(best_cand, raw_clip_path)
            raw_download_paths.append(raw_clip_path)

            # Update scene record with full attribution & licensing
            sc["selected_clip"] = raw_clip_filename
            sc["provider"] = best_cand.provider
            sc["provider_asset_id"] = best_cand.provider_asset_id
            sc["source_url"] = best_cand.source_url
            sc["licence_name"] = best_cand.licence_name
            sc["licence_url"] = best_cand.licence_url
            sc["attribution"] = best_cand.attribution
            sc["creator"] = best_cand.creator
            sc["is_ai_generated"] = best_cand.is_ai_generated
            sc["relevance_score"] = score
            sc["score_method"] = self.matcher.embedding_provider
            sc["selection_reason"] = reason

        stage_timings["footage_search_and_matching"] = round(time.time() - s5_start, 3)

        # ---------------------------------------------------------
        # STAGE 6: Aspect-Ratio Scene Rendering (75%)
        # ---------------------------------------------------------
        s6_start = time.time()
        self.update_progress("scene_rendering", 75)
        # Dictionary of aspect_ratio -> list of rendered segment paths
        rendered_segments_by_ratio: Dict[str, List[str]] = {r: [] for r in aspect_ratios}

        for idx, sc in enumerate(scenes):
            raw_path = raw_download_paths[idx]
            dur = sc["duration"]
            sc["aspect_ratio_outputs"] = {}

            for ratio in aspect_ratios:
                ratio_clean = ratio.replace(":", "_")
                seg_filename = f"segment_s{idx + 1}_{ratio_clean}.mp4"
                seg_path = str(self.work_dir / seg_filename)
                SceneRenderer.render_scene_segment(
                    raw_clip_path=raw_path,
                    duration=dur,
                    aspect_ratio=ratio,
                    output_path=seg_path,
                )
                rendered_segments_by_ratio[ratio].append(seg_path)
                sc["aspect_ratio_outputs"][ratio] = seg_filename

        stage_timings["scene_rendering"] = round(time.time() - s6_start, 3)

        # ---------------------------------------------------------
        # STAGE 7: SRT Captions & Final Multi-Ratio Composition (90%)
        # ---------------------------------------------------------
        s7_start = time.time()
        self.update_progress("video_composition", 90)

        # Generate SRT captions
        srt_path = str(self.work_dir / "captions.srt")
        SRTGenerator.generate_srt_from_scenes(scenes, srt_path)

        output_video_info: Dict[str, Any] = {}
        result_links: Dict[str, Any] = {
            "captions_srt": self.storage.save_file(srt_path, f"jobs/{self.job_id}/captions.srt"),
            "videos": {},
        }

        for ratio in aspect_ratios:
            ratio_clean = ratio.replace(":", "_")
            final_video_name = f"brollforge_{self.job_id}_{ratio_clean}.mp4"
            final_video_path = str(self.work_dir / final_video_name)

            val_info = VideoComposer.compose_video(
                segment_paths=rendered_segments_by_ratio[ratio],
                narration_audio_path=audio_path,
                aspect_ratio=ratio,
                output_video_path=final_video_path,
                srt_subtitles_path=srt_path,
                burn_captions=captions_cfg.get("burn_in", True),
            )
            output_video_info[ratio] = val_info
            # Upload to storage
            video_url = self.storage.save_file(final_video_path, f"jobs/{self.job_id}/{final_video_name}")
            result_links["videos"][ratio] = {
                "url": video_url,
                "width": val_info["width"],
                "height": val_info["height"],
                "duration": val_info["duration"],
                "file_size": val_info["file_size"],
                "aspect_ratio": ratio,
            }

        stage_timings["video_composition"] = round(time.time() - s7_start, 3)

        # ---------------------------------------------------------
        # STAGE 8: Timeline.json & Manifest.json (97%)
        # ---------------------------------------------------------
        s8_start = time.time()
        self.update_progress("generating_manifests", 97)

        timeline_path = str(self.work_dir / "timeline.json")
        timeline_data = ManifestGenerator.generate_timeline(
            job_id=self.job_id,
            scenes=scenes,
            aspect_ratios=aspect_ratios,
            total_duration=total_audio_duration,
            output_path=timeline_path,
        )
        result_links["timeline"] = self.storage.save_file(timeline_path, f"jobs/{self.job_id}/timeline.json")

        manifest_path = str(self.work_dir / "manifest.json")
        manifest_data = ManifestGenerator.generate_manifest(
            job_id=self.job_id,
            input_type=input_type,
            input_file_metadata=audio_probe,
            audio_duration=total_audio_duration,
            transcription_info=transcript_data.get("model_info", {}),
            tts_info=tts_info,
            embedding_info={"provider": self.matcher.embedding_provider, "method": "cosine_similarity_tfidf"},
            footage_providers=[{"provider": p} for p in set(s["provider"] for s in scenes if s.get("provider"))],
            aspect_ratios=aspect_ratios,
            output_files=result_links,
            scene_count=len(scenes),
            processing_timings=stage_timings,
            total_processing_time=time.time() - start_time,
            provider_licences=[
                {
                    "provider": s.get("provider"),
                    "licence_name": s.get("licence_name"),
                    "licence_url": s.get("licence_url"),
                    "attribution": s.get("attribution"),
                    "is_ai_generated": s.get("is_ai_generated", False),
                }
                for s in scenes
            ],
            warnings=warnings,
            errors=[],
            fallbacks_used=list(set(fallbacks_used)),
            output_path=manifest_path,
        )
        result_links["manifest"] = self.storage.save_file(manifest_path, f"jobs/{self.job_id}/manifest.json")
        stage_timings["generating_manifests"] = round(time.time() - s8_start, 3)

        # ---------------------------------------------------------
        # STAGE 9: Complete Job Record & Webhook Notification (100%)
        # ---------------------------------------------------------
        total_time = round(time.time() - start_time, 3)
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == self.job_id).first()
            if job:
                job.status = "succeeded"
                job.progress = 100
                job.stage = "completed"
                job.audio_metadata = audio_probe
                job.transcript_data = transcript_data
                job.timeline_data = timeline_data
                job.manifest_data = manifest_data
                job.result_links = result_links
                job.warnings = warnings
                job.completed_at = datetime.now(timezone.utc)

                # Persist SceneModel records in DB
                for idx, sc in enumerate(scenes):
                    scene_uuid = sc.get("scene_id") or str(uuid.uuid4())
                    sm = SceneModel(
                        id=scene_uuid,
                        job_id=self.job_id,
                        scene_index=idx,
                        text=sc["text"],
                        start_time=sc["start_time"],
                        end_time=sc["end_time"],
                        duration=sc["duration"],
                        visual_hint=sc.get("visual_hint"),
                        semantic_description=sc.get("semantic_description"),
                        search_query=sc["search_query"],
                        selected_clip_id=sc.get("selected_clip"),
                        provider=sc.get("provider"),
                        provider_asset_id=sc.get("provider_asset_id"),
                        source_url=sc.get("source_url"),
                        licence_name=sc.get("licence_name"),
                        licence_url=sc.get("licence_url"),
                        attribution=sc.get("attribution"),
                        creator=sc.get("creator"),
                        is_ai_generated=sc.get("is_ai_generated", False),
                        relevance_score=sc.get("relevance_score", 0.0),
                        score_method=sc.get("score_method", "semantic_similarity"),
                        selection_reason=sc.get("selection_reason"),
                        aspect_ratio_outputs=sc.get("aspect_ratio_outputs", {}),
                    )
                    db.add(sm)
                db.commit()
        finally:
            db.close()

        # Send Signed HMAC Callback if URL provided
        if callback_url:
            await self._dispatch_webhook(callback_url, {
                "job_id": self.job_id,
                "status": "succeeded",
                "progress": 100,
                "result_links": result_links,
                "processing_time": total_time,
            })

        logger.info(f"Job {self.job_id} successfully completed in {total_time}s")
        return result_links

    async def _dispatch_webhook(self, url: str, payload: Dict[str, Any]):
        body = json.dumps(payload, sort_keys=True)
        secret = settings.WEBHOOK_SECRET.encode("utf-8")
        signature = hmac.new(secret, body.encode("utf-8"), hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-IncuBrix-Signature": signature,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, content=body, headers=headers)
                logger.info(f"Dispatched signed webhook for job {self.job_id} to {url}")
        except Exception as e:
            logger.warning(f"Failed to deliver callback webhook to {url}: {e}")
