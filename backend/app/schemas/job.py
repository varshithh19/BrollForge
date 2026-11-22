from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class CaptionsConfig(BaseModel):
    burn_in: bool = True
    srt: bool = True


class SceneInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    visual_hint: Optional[str] = Field(None, max_length=500)


class CreateJobRequest(BaseModel):
    audio_url: Optional[str] = None
    script: Optional[str] = Field(None, max_length=20000)
    scenes: Optional[List[SceneInput]] = None
    voice: Optional[str] = "en-IN-female"
    aspect_ratios: List[str] = Field(default_factory=lambda: ["16:9", "9:16"])
    style: str = "bright, modern, real-world footage"
    avoid: List[str] = Field(default_factory=lambda: ["people's faces", "alcohol"])
    captions: CaptionsConfig = Field(default_factory=CaptionsConfig)
    callback_url: Optional[str] = None

    @field_validator("aspect_ratios")
    @classmethod
    def validate_aspect_ratios(cls, v: List[str]) -> List[str]:
        valid_ratios = {"16:9", "9:16", "1:1"}
        if not v:
            raise ValueError("At least one aspect ratio must be selected")
        for ratio in v:
            if ratio not in valid_ratios:
                raise ValueError(f"Unsupported aspect ratio: '{ratio}'. Must be one of: 16:9, 9:16, 1:1")
        return list(dict.fromkeys(v))  # deduplicate preserving order


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    stage: str
    created_at: datetime
    updated_at: datetime
    result_links: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    error: Optional[Dict[str, Any]] = None


class SceneSwapRequest(BaseModel):
    clip_id: Optional[str] = None
    visual_hint: Optional[str] = None


class TimelineScene(BaseModel):
    scene_id: str
    text: str
    start_time: float
    end_time: float
    duration: float
    visual_hint: Optional[str] = None
    semantic_description: Optional[str] = None
    search_query: str
    selected_clip: Optional[str] = None
    provider: Optional[str] = None
    provider_asset_id: Optional[str] = None
    source_url: Optional[str] = None
    licence_name: Optional[str] = None
    licence_url: Optional[str] = None
    attribution: Optional[str] = None
    creator: Optional[str] = None
    is_ai_generated: bool = False
    relevance_score: float = 0.0
    score_method: str = "semantic_similarity"
    selection_reason: Optional[str] = None
    aspect_ratio_outputs: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class TimelineOutput(BaseModel):
    job_id: str
    total_duration: float
    scene_count: int
    aspect_ratios: List[str]
    scenes: List[TimelineScene]


class ManifestOutput(BaseModel):
    job_id: str
    app_version: str
    creation_time: str
    input_type: str
    input_file_metadata: Dict[str, Any]
    audio_duration: float
    transcription: Dict[str, Any]
    tts: Optional[Dict[str, Any]] = None
    embedding: Dict[str, Any]
    footage_providers: List[Dict[str, Any]]
    ffmpeg_version: str
    settings: Dict[str, Any]
    aspect_ratios: List[str]
    output_files: Dict[str, Any]
    scene_count: int
    processing_timings: Dict[str, float]
    total_processing_time: float
    estimated_cost: Optional[float] = None
    currency: str = "USD"
    cost_calculation_method: str = "formula_based_api_and_compute"
    provider_licences: List[Dict[str, Any]]
    ai_generated_flags: Dict[str, bool]
    warnings: List[str]
    errors: List[str]
    fallbacks_used: List[str]
    random_seed: Optional[int] = None
