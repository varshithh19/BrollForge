import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
from backend.app.config.settings import settings
from backend.app.services.footage.models import FootageCandidate
from backend.app.services.footage.provider_base import FootageProvider


class MockFootageProvider(FootageProvider):
    """
    Mock provider for automated testing and CI pipelines.
    Explicitly labelled as non-production test fixtures.
    """

    def __init__(self, test_fixtures_dir: str = "./storage/temp/mock_fixtures"):
        self.fixtures_dir = Path(test_fixtures_dir).resolve()
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "mock_test_provider"

    @property
    def is_available(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        orientation: Optional[str] = None,
        limit: int = 5,
    ) -> List[FootageCandidate]:
        candidates = []
        for i in range(min(limit, 4)):
            cid = f"mock_asset_{i + 1}_{abs(hash(query)) % 10000}"
            candidates.append(
                FootageCandidate(
                    provider=self.name,
                    provider_asset_id=cid,
                    preview_url=f"http://test.local/mock_preview_{cid}.jpg",
                    download_url=f"http://test.local/mock_{cid}.mp4",
                    source_url="http://test.local/mock_source",
                    licence_name="Internal Automated Test Fixture",
                    licence_url="https://test.local/license/test-only",
                    attribution="Mock Test Fixture (Not For Production)",
                    creator="IncuBrix QA Fixture Engine",
                    media_type="video",
                    duration=8.0,
                    width=1920,
                    height=1080,
                    orientation=orientation or "landscape",
                    is_ai_generated=False,
                    raw_metadata={"query": query, "is_mock": True},
                )
            )
        return candidates

    async def download_clip(self, candidate: FootageCandidate, target_path: str) -> str:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        # Generate master fixture once if not present, then copy
        master = self.fixtures_dir / "master_test_clip.mp4"
        if not master.exists():
            cmd = [
                settings.FFMPEG_PATH,
                "-y",
                "-f", "lavfi",
                "-i", "testsrc=size=1920x1080:rate=30",
                "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-c:v", "libx264",
                "-t", "6",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-shortest",
                str(master),
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        if str(master.resolve()) != str(target.resolve()):
            shutil.copy2(master, target)

        return str(target)
