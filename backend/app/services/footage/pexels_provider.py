import httpx
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.config.settings import settings
from backend.app.core.errors import FootageNotFoundError
from backend.app.core.logging import logger
from backend.app.services.footage.models import FootageCandidate
from backend.app.services.footage.provider_base import FootageProvider


class PexelsProvider(FootageProvider):
    """
    Real footage provider interfacing with the official Pexels Video Search API.
    Commercial terms: Pexels License explicitly allows commercial use and modification.
    """

    BASE_URL = "https://api.pexels.com/videos/search"
    LICENSE_NAME = "Pexels License (Commercial Use Allowed)"
    LICENSE_URL = "https://www.pexels.com/license/"

    def __init__(self, api_key: Optional[str] = settings.PEXELS_API_KEY):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "pexels"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def search(
        self,
        query: str,
        orientation: Optional[str] = None,
        limit: int = 10,
    ) -> List[FootageCandidate]:
        if not self.is_available:
            logger.info("Pexels API key not configured; skipping Pexels provider.")
            return []

        headers = {"Authorization": self.api_key}
        params: Dict[str, Any] = {
            "query": query,
            "per_page": min(limit, 15),
        }
        if orientation in {"landscape", "portrait", "square"}:
            params["orientation"] = orientation

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.BASE_URL, headers=headers, params=params)
                if resp.status_code == 401:
                    logger.warning("Pexels API key invalid (HTTP 401)")
                    return []
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning(f"Pexels search API call failed: {e}")
            return []

        candidates = []
        for video in data.get("videos", []):
            vid_id = str(video.get("id"))
            duration = float(video.get("duration", 0.0))
            width = int(video.get("width", 1920))
            height = int(video.get("height", 1080))
            user = video.get("user", {})
            creator = user.get("name") or "Pexels Contributor"
            source_url = video.get("url") or f"https://www.pexels.com/video/{vid_id}/"

            # Select best HD/FHD mp4 video file
            video_files = video.get("video_files", [])
            # Sort descending by resolution (preference for 1080p)
            mp4_files = [f for f in video_files if f.get("file_type") == "video/mp4"]
            if not mp4_files:
                continue

            # Find closest to 1080p
            best_file = max(mp4_files, key=lambda f: (f.get("width", 0) <= 1920, f.get("width", 0)))
            download_url = best_file.get("link")
            preview_url = video.get("image") or download_url

            orient = "landscape"
            if height > width:
                orient = "portrait"
            elif height == width:
                orient = "square"

            candidates.append(
                FootageCandidate(
                    provider=self.name,
                    provider_asset_id=vid_id,
                    preview_url=preview_url,
                    download_url=download_url,
                    source_url=source_url,
                    licence_name=self.LICENSE_NAME,
                    licence_url=self.LICENSE_URL,
                    attribution=f"Video by {creator} from Pexels",
                    creator=creator,
                    media_type="video",
                    duration=duration,
                    width=width,
                    height=height,
                    orientation=orient,
                    is_ai_generated=False,
                    raw_metadata=video,
                )
            )

        logger.info(f"Pexels search returned {len(candidates)} candidates for query '{query}'")
        return candidates

    async def download_clip(self, candidate: FootageCandidate, target_path: str) -> str:
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(candidate.download_url)
            resp.raise_for_status()
            with open(target_path, "wb") as f:
                f.write(resp.content)

        logger.info(f"Downloaded Pexels clip {candidate.provider_asset_id} to {target_path}")
        return target_path
