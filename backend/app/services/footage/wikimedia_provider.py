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
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:video {query}",
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
            if not url or not (url.endswith(".webm") or url.endswith(".mp4") or url.endswith(".ogv")):
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
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        headers = {"User-Agent": "BrollForgeVideoEngine/1.0 (incubrix-assessment; contact@brollforge.local)"}
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            resp = await client.get(candidate.download_url, headers=headers)
            resp.raise_for_status()
            with open(target_path, "wb") as f:
                f.write(resp.content)

        logger.info(f"Downloaded Wikimedia clip {candidate.provider_asset_id} to {target_path}")
        return target_path
