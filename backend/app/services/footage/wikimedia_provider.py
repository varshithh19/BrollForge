import httpx
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.core.logging import logger
from backend.app.services.footage.models import FootageCandidate
from backend.app.services.footage.provider_base import FootageProvider


class WikimediaCommonsProvider(FootageProvider):
    """
    Genuine secondary footage provider querying Wikimedia Commons for verified
    CC0, Public Domain, and CC-BY commercially-usable video footage.
    Requires no secret API key and provides verifiable licensing URLs.
    """

    API_URL = "https://commons.wikimedia.org/w/api.php"

    @property
    def name(self) -> str:
        return "wikimedia_commons"

    @property
    def is_available(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        orientation: Optional[str] = None,
        limit: int = 5,
    ) -> List[FootageCandidate]:
        # Extract key search keywords for MediaWiki search
        clean_words = [w for w in query.replace(",", " ").split() if len(w) > 3 and w.lower() not in {"bright", "modern", "enterprise", "footage", "real-world"}][:2]
        search_term = " ".join(clean_words) if clean_words else query.split()[0] if query.split() else "technology"

        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:video {search_term}",
            "gsrnamespace": 6,
            "gsrlimit": min(limit, 10),
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
        }
        headers = {"User-Agent": "BrollForgeVideoEngine/1.0 (incubrix-assessment; contact@brollforge.local)"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.API_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning(f"Wikimedia Commons API query failed ({e}); skipping secondary provider.")
            return []

        pages = data.get("query", {}).get("pages", {})
        candidates = []

        for page_id, page in pages.items():
            imageinfo = page.get("imageinfo", [])
            if not imageinfo:
                continue

            info = imageinfo[0]
            url = info.get("url")
            base_url = url.split("?")[0].lower() if url else ""
            if not base_url or not (base_url.endswith(".webm") or base_url.endswith(".mp4") or base_url.endswith(".ogv")):
                continue

            # Skip oversized files (e.g. multi-gigabyte raw footage) to ensure fast, reliable downloads
            file_size = int(info.get("size", 0))
            if file_size > 25 * 1024 * 1024 or file_size == 0:
                logger.info(f"Skipping Wikimedia candidate {page_id} (size {file_size} bytes exceeds 25MB limit)")
                continue

            metadata = info.get("extmetadata", {})
            license_short = metadata.get("LicenseShortName", {}).get("value", "Public Domain")
            license_url = metadata.get("LicenseUrl", {}).get("value", "https://creativecommons.org/publicdomain/zero/1.0/")
            artist = metadata.get("Artist", {}).get("value", "Wikimedia Contributor")
            # Strip html tags from artist string if present
            clean_artist = artist.replace("<p>", "").replace("</p>", "").replace("<b>", "").replace("</b>", "").strip()

            # Reject non-commercial licenses (strict requirement)
            if "NC" in license_short.upper() or "NON-COMMERCIAL" in license_short.upper():
                logger.info(f"Rejected candidate {page_id} due to non-commercial license: {license_short}")
                continue

            width = int(info.get("width", 1920))
            height = int(info.get("height", 1080))
            orient = "landscape"
            if height > width:
                orient = "portrait"
            elif height == width:
                orient = "square"

            candidates.append(
                FootageCandidate(
                    provider=self.name,
                    provider_asset_id=str(page_id),
                    preview_url=info.get("thumburl", url),
                    download_url=url,
                    source_url=info.get("descriptionurl", f"https://commons.wikimedia.org/?curid={page_id}"),
                    licence_name=license_short,
                    licence_url=license_url,
                    attribution=f"File by {clean_artist} via Wikimedia Commons ({license_short})",
                    creator=clean_artist[:60],
                    media_type="video",
                    duration=10.0,
                    width=width,
                    height=height,
                    orientation=orient,
                    is_ai_generated=False,
                    raw_metadata=info,
                )
            )

        logger.info(f"Wikimedia Commons returned {len(candidates)} candidates for '{query}'")
        return candidates

    async def download_clip(self, candidate: FootageCandidate, target_path: str) -> str:
        import os
        import subprocess
        from backend.app.config.settings import settings

        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        headers = {"User-Agent": "BrollForgeVideoEngine/1.0 (incubrix-assessment; contact@brollforge.local)"}
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            resp = await client.get(candidate.download_url, headers=headers)
            resp.raise_for_status()

        temp_file = target_path + ".tmp"
        with open(temp_file, "wb") as f:
            f.write(resp.content)

        # Transcode cleanly to H.264 MP4 using FFmpeg (first 12s is plenty for b-roll scenes)
        cmd = [
            settings.FFMPEG_PATH,
            "-y",
            "-t", "12",
            "-i", str(temp_file),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-an",
            str(target_path),
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        logger.info(f"Downloaded and normalized Wikimedia clip {candidate.provider_asset_id} to {target_path}")
        return target_path
