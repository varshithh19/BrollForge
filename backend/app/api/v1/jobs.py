import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from backend.app.config.settings import settings
from backend.app.core.errors import (
    IdempotencyConflictError,
    JobNotFoundError,
    ValidationError,
)
from backend.app.core.logging import logger
from backend.app.db.session import get_db
from backend.app.models.job import Job, SceneModel
from backend.app.schemas.job import (
    CreateJobRequest,
    JobResponse,
    ManifestOutput,
    SceneSwapRequest,
    TimelineOutput,
)
from backend.app.services.rendering.clip_swapper import ClipSwapper
from backend.app.utils.security import validate_url_safety
from backend.app.workers.queue import get_queue_service

router = APIRouter()


def compute_request_hash(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@router.post(
    "/broll/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new B-roll video generation job",
)
@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def create_broll_job(
    request: CreateJobRequest,
    response: Response,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    # Validate mutual exclusivity & presence of input
    has_audio_url = bool(request.audio_url)
    has_script = bool(request.script and request.script.strip())
    has_scenes = bool(request.scenes)

    input_count = sum([has_audio_url, has_script, has_scenes])
    if input_count == 0:
        raise ValidationError("Must provide at least one of: 'audio_url', 'script', or 'scenes'")

    # SSRF Protection
    if request.audio_url:
        validate_url_safety(request.audio_url)
    if request.callback_url:
        validate_url_safety(request.callback_url)

    # Determine input type & payload
    if has_script or has_scenes:
        input_type = "script"
        script_text = request.script or " ".join(s.text for s in request.scenes)
        input_payload = {
            "script": script_text,
            "scenes": [s.model_dump() for s in (request.scenes or [])],
            "voice": request.voice,
        }
    else:
        input_type = "audio_url"
        input_payload = {"audio_url": request.audio_url}

    full_payload = {
        "input_type": input_type,
        "input_payload": input_payload,
        "aspect_ratios": request.aspect_ratios,
        "style": request.style,
        "avoid": request.avoid,
        "captions": request.captions.model_dump() if request.captions else {},
    }
    req_hash = compute_request_hash(full_payload)

    # Handle Idempotency
    if idempotency_key:
        existing = db.query(Job).filter(Job.idempotency_key == idempotency_key).first()
        if existing:
            if existing.request_hash == req_hash:
                logger.info(f"Idempotent request matched existing job {existing.id}")
                response.status_code = status.HTTP_200_OK if existing.status == "succeeded" else status.HTTP_202_ACCEPTED
                return JobResponse(
                    job_id=existing.id,
                    status=existing.status,
                    progress=existing.progress,
                    stage=existing.stage,
                    created_at=existing.created_at,
                    updated_at=existing.updated_at,
                    result_links=existing.result_links or {},
                    warnings=existing.warnings or [],
                    error=existing.error,
                )
            else:
                raise IdempotencyConflictError("Idempotency-Key already used with a different request payload.")

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        idempotency_key=idempotency_key,
        request_hash=req_hash,
        status="queued",
        progress=0,
        stage="queued",
        input_type=input_type,
        input_payload=input_payload,
        aspect_ratios=request.aspect_ratios,
        style=request.style,
        avoid=request.avoid,
        captions_config=request.captions.model_dump() if request.captions else {},
        callback_url=request.callback_url,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue background processing
    queue_service = get_queue_service()
    queue_service.enqueue_job(job_id=job.id)

    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result_links={},
        warnings=[],
        error=None,
    )


@router.post(
    "/broll/jobs/upload",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload an audio voiceover file (MP3, WAV, M4A) and create a job",
)
@router.post(
    "/jobs/upload",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def upload_audio_job(
    file: UploadFile = File(...),
    aspect_ratios: str = Query('["16:9", "9:16"]'),
    style: str = Query("bright, modern, real-world footage"),
    avoid: str = Query('["people\'s faces", "alcohol"]'),
    burn_captions: bool = Query(True),
    callback_url: Optional[str] = Query(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    if callback_url:
        validate_url_safety(callback_url)

    ext = Path(file.filename or "audio.mp3").suffix.lower()
    if ext not in {".mp3", ".wav", ".m4a"}:
        raise ValidationError(f"Invalid file extension '{ext}'. Must be .mp3, .wav, or .m4a")

    job_id = str(uuid.uuid4())
    job_dir = Path(f"./storage/jobs/{job_id}").resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
    stored_path = str(job_dir / f"uploaded_audio{ext}")

    with open(stored_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        ratios_parsed = json.loads(aspect_ratios)
    except Exception:
        ratios_parsed = ["16:9"]

    try:
        avoid_parsed = json.loads(avoid)
    except Exception:
        avoid_parsed = []

    input_payload = {"file_path": stored_path, "filename": file.filename}

    job = Job(
        id=job_id,
        idempotency_key=idempotency_key,
        status="queued",
        progress=0,
        stage="queued",
        input_type="audio_upload",
        input_payload=input_payload,
        aspect_ratios=ratios_parsed,
        style=style,
        avoid=avoid_parsed,
        captions_config={"burn_in": burn_captions, "srt": True},
        callback_url=callback_url,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    queue_service = get_queue_service()
    queue_service.enqueue_job(job_id=job.id)

    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result_links={},
        warnings=[],
        error=None,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse, summary="Get job status and progress")
@router.get("/broll/jobs/{job_id}", response_model=JobResponse, include_in_schema=False)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise JobNotFoundError(job_id)

    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result_links=job.result_links or {},
        warnings=job.warnings or [],
        error=job.error,
    )


@router.get("/jobs", summary="List recent jobs")
@router.get("/broll/jobs", include_in_schema=False)
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    jobs = db.query(Job).order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
    total = db.query(Job).count()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "jobs": [
            {
                "job_id": j.id,
                "status": j.status,
                "progress": j.progress,
                "stage": j.stage,
                "input_type": j.input_type,
                "aspect_ratios": j.aspect_ratios,
                "created_at": j.created_at,
                "result_links": j.result_links,
                "error": j.error,
            }
            for j in jobs
        ],
    }


@router.get("/jobs/{job_id}/timeline", summary="Get job scene timeline breakdown")
@router.get("/broll/jobs/{job_id}/timeline", include_in_schema=False)
async def get_job_timeline(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise JobNotFoundError(job_id)
    if not job.timeline_data:
        raise HTTPException(status_code=404, detail="Timeline not yet generated for this job")
    return job.timeline_data


@router.get("/jobs/{job_id}/manifest", summary="Get full job manifest artifact")
@router.get("/broll/jobs/{job_id}/manifest", include_in_schema=False)
async def get_job_manifest(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise JobNotFoundError(job_id)
    if not job.manifest_data:
        raise HTTPException(status_code=404, detail="Manifest not yet generated for this job")
    return job.manifest_data


@router.get("/jobs/{job_id}/captions", summary="Download captions SRT file")
@router.get("/broll/jobs/{job_id}/captions", include_in_schema=False)
async def get_job_captions(job_id: str):
    srt_path = Path(f"./storage/jobs/{job_id}/captions.srt").resolve()
    if not srt_path.exists():
        raise HTTPException(status_code=404, detail="Captions SRT file not found for this job")
    return FileResponse(srt_path, media_type="text/plain", filename=f"captions_{job_id}.srt")


@router.get("/jobs/{job_id}/results", summary="Get finished video results and download URLs")
@router.get("/broll/jobs/{job_id}/results", include_in_schema=False)
async def get_job_results(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise JobNotFoundError(job_id)
    return {
        "job_id": job.id,
        "status": job.status,
        "result_links": job.result_links or {},
    }


@router.post("/jobs/{job_id}/scenes/{scene_id}/swap", summary="Swap scene clip and rerender affected video segment")
@router.post("/broll/jobs/{job_id}/scenes/{scene_id}/swap", include_in_schema=False)
@router.post("/broll/jobs/{job_id}/swap-clip", include_in_schema=False)
async def swap_scene(
    job_id: str,
    scene_id: Optional[str] = None,
    req: SceneSwapRequest = Body(...),
):
    target_scene_id = scene_id or req.scene_id
    if not target_scene_id:
        raise ValidationError("Must provide scene_id either in path or body")
    res = await ClipSwapper.swap_scene_clip(
        job_id=job_id,
        scene_id=target_scene_id,
        new_clip_id=req.clip_id,
        new_visual_hint=req.visual_hint,
    )
    return res
