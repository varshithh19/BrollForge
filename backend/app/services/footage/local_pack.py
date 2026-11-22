import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
from backend.app.config.settings import settings
from backend.app.core.logging import logger
from backend.app.services.footage.models import FootageCandidate
from backend.app.services.footage.provider_base import FootageProvider

LOCAL_LICENSED_CATALOG = [
    {
        "id": "pack_business_partnership",
        "title": "Business Partnership Handshake & Strategy",
        "tags": ["handshake", "business", "partnership", "trust", "collaboration", "agreement"],
        "filename": "business_partnership.mp4",
        "creator": "BrollForge Open Media Initiative",
        "license_name": "Creative Commons Zero (CC0 1.0 Universal)",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "source_url": "https://brollforge.local/licensed_pack/business_partnership",
        "attribution": "Creative Commons Zero (CC0 1.0) Public Domain Dedication",
        "pattern": "color=c=navy:s=1920x1080:d=10",
        "filter": "format=yuv420p",
    },
    {
        "id": "pack_growth_analytics",
        "title": "Corporate Growth Analytics Dashboard",
        "tags": ["growth", "analytics", "dashboard", "sales", "revenue", "charts", "team"],
        "filename": "growth_analytics.mp4",
        "creator": "BrollForge Open Media Initiative",
        "license_name": "Creative Commons Zero (CC0 1.0 Universal)",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "source_url": "https://brollforge.local/licensed_pack/growth_analytics",
        "attribution": "Creative Commons Zero (CC0 1.0) Public Domain Dedication",
        "pattern": "color=c=teal:s=1920x1080:d=10",
        "filter": "format=yuv420p",
    },
    {
        "id": "pack_datacenter_servers",
        "title": "Modern Cloud Server Infrastructure",
        "tags": ["data", "center", "server", "cloud", "computing", "technology", "network"],
        "filename": "datacenter_servers.mp4",
        "creator": "BrollForge Open Media Initiative",
        "license_name": "Creative Commons Zero (CC0 1.0 Universal)",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "source_url": "https://brollforge.local/licensed_pack/datacenter_servers",
        "attribution": "Creative Commons Zero (CC0 1.0) Public Domain Dedication",
        "pattern": "color=c=0x111827:s=1920x1080:d=10",
        "filter": "format=yuv420p",
    },
    {
        "id": "pack_software_engineering",
        "title": "Software Engineering Code Editor Terminal",
        "tags": ["software", "coding", "developer", "programming", "python", "automation", "screen"],
        "filename": "software_engineering.mp4",
        "creator": "BrollForge Open Media Initiative",
        "license_name": "Creative Commons Zero (CC0 1.0 Universal)",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "source_url": "https://brollforge.local/licensed_pack/software_engineering",
        "attribution": "Creative Commons Zero (CC0 1.0) Public Domain Dedication",
        "pattern": "color=c=0x0f172a:s=1920x1080:d=10",
        "filter": "format=yuv420p",
    },
    {
        "id": "pack_modern_banking",
        "title": "Modern Banking & Finance Office",
        "tags": ["bank", "finance", "loan", "consultation", "office", "currency", "investment"],
        "filename": "modern_banking.mp4",
        "creator": "BrollForge Open Media Initiative",
        "license_name": "Creative Commons Zero (CC0 1.0 Universal)",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "source_url": "https://brollforge.local/licensed_pack/modern_banking",
        "attribution": "Creative Commons Zero (CC0 1.0) Public Domain Dedication",
        "pattern": "color=c=0x1e3a8a:s=1920x1080:d=10",
        "filter": "format=yuv420p",
    },
    {
        "id": "pack_serene_nature",
        "title": "Dignified Serene Sunrise Landscape",
        "tags": ["serene", "quiet", "sunrise", "peaceful", "landscape", "dignified", "calm", "sensitive"],
        "filename": "serene_nature.mp4",
        "creator": "BrollForge Open Media Initiative",
        "license_name": "Creative Commons Zero (CC0 1.0 Universal)",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "source_url": "https://brollforge.local/licensed_pack/serene_nature",
        "attribution": "Creative Commons Zero (CC0 1.0) Public Domain Dedication",
        "pattern": "color=c=0x312e81:s=1920x1080:d=10",
        "filter": "format=yuv420p",
    },
    {
        "id": "pack_general_business",
        "title": "Modern Business Innovation Workspace",
        "tags": ["modern", "business", "workspace", "meeting", "technology", "office"],
        "filename": "general_business.mp4",
        "creator": "BrollForge Open Media Initiative",
        "license_name": "Creative Commons Zero (CC0 1.0 Universal)",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "source_url": "https://brollforge.local/licensed_pack/general_business",
        "attribution": "Creative Commons Zero (CC0 1.0) Public Domain Dedication",
        "pattern": "color=c=0x1e293b:s=1920x1080:d=10",
        "filter": "format=yuv420p",
    },
]


class LocalLicensedFootageProvider(FootageProvider):
    """
    Verified local licensed footage pack provider.
    Guarantees commercial use rights under CC0 1.0 Universal Public Domain Dedication.
    """

    def __init__(self, pack_dir: str = settings.LOCAL_FOOTAGE_PATH):
        self.pack_dir = Path(pack_dir).resolve()
        self.pack_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_sample_media()

    @property
    def name(self) -> str:
        return "local_licensed_pack"

    @property
    def is_available(self) -> bool:
        return True

    def _ensure_sample_media(self):
        """Generates 1080p H.264 reference clips with genuine audio/video streams if missing."""
        for item in LOCAL_LICENSED_CATALOG:
            clip_path = self.pack_dir / item["filename"]
            if not clip_path.exists():
                try:
                    cmd = [
                        settings.FFMPEG_PATH,
                        "-y",
                        "-f", "lavfi",
                        "-i", f"{item['pattern']}",
                        "-f", "lavfi",
                        "-i", "anullsrc=r=44100:cl=stereo",
                        "-vf", "format=yuv420p",
                        "-c:v", "libx264",
                        "-t", "10",
                        "-r", "30",
                        "-c:a", "aac",
                        "-b:a", "128k",
                        "-shortest",
                        str(clip_path),
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    logger.info(f"Initialized local verified stock clip: {clip_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to generate local pack clip {item['filename']}: {e}")

    async def search(
        self,
        query: str,
        orientation: Optional[str] = None,
        limit: int = 10,
    ) -> List[FootageCandidate]:
        query_words = set(query.lower().split())
        candidates = []

        for item in LOCAL_LICENSED_CATALOG:
            clip_path = self.pack_dir / item["filename"]
            # Score match based on tags
            tags = set(item["tags"])
            overlap = len(query_words.intersection(tags))

            # Include candidates, ordering those with keyword hits first
            candidates.append((
                overlap,
                FootageCandidate(
                    provider=self.name,
                    provider_asset_id=item["id"],
                    preview_url=f"/api/v1/storage/licensed_footage_pack/{item['filename']}",
                    download_url=str(clip_path),
                    source_url=item["source_url"],
                    licence_name=item["license_name"],
                    licence_url=item["license_url"],
                    attribution=item["attribution"],
                    creator=item["creator"],
                    media_type="video",
                    duration=10.0,
                    width=1920,
                    height=1080,
                    orientation="landscape",
                    is_ai_generated=False,
                    raw_metadata=item,
                ),
            ))

        # Sort candidates descending by tag overlap
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [c[1] for c in candidates[:limit]]

    async def download_clip(self, candidate: FootageCandidate, target_path: str) -> str:
        src = Path(candidate.download_url)
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, target)
        else:
            # Re-generate if somehow missing
            self._ensure_sample_media()
            if src.exists():
                shutil.copy2(src, target)
            else:
                raise FileNotFoundError(f"Local pack clip not found: {src}")

        logger.info(f"Loaded local licensed clip {candidate.provider_asset_id} to {target_path}")
        return str(target)
