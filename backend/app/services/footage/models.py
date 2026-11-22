from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class FootageCandidate(BaseModel):
    provider: str
    provider_asset_id: str
    preview_url: str
    download_url: str
    source_url: str
    licence_name: str
    licence_url: str
    attribution: str
    creator: str
    media_type: str = "video"
    duration: float
    width: int
    height: int
    orientation: str = "landscape"  # landscape, portrait, square
    is_ai_generated: bool = False
    content_hash: Optional[str] = None
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
