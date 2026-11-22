from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    idempotency_key = Column(String(128), nullable=True, index=True)
    request_hash = Column(String(64), nullable=True)

    status = Column(String(32), default="queued", index=True)  # queued, running, succeeded, failed
    progress = Column(Integer, default=0)
    stage = Column(String(64), default="queued")

    input_type = Column(String(32), nullable=False)  # audio_upload, audio_url, script, scenes
    input_payload = Column(JSON, default=dict)
    
    aspect_ratios = Column(JSON, default=list)  # ["16:9", "9:16", "1:1"]
    style = Column(String(256), default="bright, modern, real-world footage")
    avoid = Column(JSON, default=list)  # ["people's faces", "alcohol", ...]
    captions_config = Column(JSON, default=lambda: {"burn_in": True, "srt": True})
    callback_url = Column(String(512), nullable=True)

    audio_metadata = Column(JSON, nullable=True)
    transcript_data = Column(JSON, nullable=True)
    timeline_data = Column(JSON, nullable=True)
    manifest_data = Column(JSON, nullable=True)
    result_links = Column(JSON, default=dict)
    warnings = Column(JSON, default=list)
    error = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    scenes = relationship("SceneModel", back_populates="job", cascade="all, delete-orphan", order_by="SceneModel.scene_index")


class SceneModel(Base):
    __tablename__ = "scenes"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(64), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    scene_index = Column(Integer, nullable=False)

    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)

    visual_hint = Column(Text, nullable=True)
    semantic_description = Column(Text, nullable=True)
    search_query = Column(String(256), nullable=False)

    selected_clip_id = Column(String(128), nullable=True)
    provider = Column(String(64), nullable=True)
    provider_asset_id = Column(String(128), nullable=True)
    source_url = Column(String(512), nullable=True)
    licence_name = Column(String(128), nullable=True)
    licence_url = Column(String(512), nullable=True)
    attribution = Column(Text, nullable=True)
    creator = Column(String(128), nullable=True)
    is_ai_generated = Column(Boolean, default=False)

    relevance_score = Column(Float, default=0.0)
    score_method = Column(String(64), default="semantic_similarity")
    selection_reason = Column(Text, nullable=True)
    aspect_ratio_outputs = Column(JSON, default=dict)
    warnings = Column(JSON, default=list)

    job = relationship("Job", back_populates="scenes")


Index("ix_scenes_job_id_index", SceneModel.job_id, SceneModel.scene_index)
