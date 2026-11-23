
import os
import re
import html
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config.settings import settings
from backend.app.core.logging import logger
from backend.app.services.footage.models import FootageCandidate
from backend.app.services.footage.provider_base import FootageProvider


class WikimediaCommonsProvider(FootageProvider):
    """
    Wikimedia Commons footage provider.

    Searches for video footage, validates licensing metadata,
    downloads selected footage, and normalizes it to H.264 MP4
    using memory-efficient FFmpeg settings.
    """

    API_URL = "https://commons.wikimedia.org/w/api.php"

    USER_AGENT = (
        "BrollForgeVideoEngine/1.0 "
        "(incubrix-assessment; contact@brollforge.local)"
    )

    MAX_FILE_SIZE = 25 * 1024 * 1024
    MIN_FILE_SIZE = 1024
    MAX_CLIP_DURATION = 12
    DOWNLOAD_TIMEOUT = 60.0
    FFMPEG_TIMEOUT = 180

    MAX_OUTPUT_DIMENSION = 1920
    MAX_ENCODER_THREADS = 2

    @property
    def name(self) -> str:
        return "wikimedia_commons"

    @property
    def is_available(self) -> bool:
        return True

    @staticmethod
    def _clean_metadata(value: Any) -> str:
        """Remove HTML markup and decode metadata entities."""
        if not value:
            return ""

        cleaned = html.unescape(str(value))
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned.strip()

    @staticmethod
    def _is_commercially_usable_license(
        license_name: str,
        license_url: str,
    ) -> bool:
        """
        Reject missing or non-commercial licensing metadata.

        This is a conservative metadata check, not a substitute
        for verifying the original licence terms.
        """
        if not license_name or not license_url:
            return False

        name = license_name.upper()

        restricted_markers = (
            "NON-COMMERCIAL",
            "NONCOMMERCIAL",
            "CC BY-NC",
            "CC BY-NC-SA",
            "CC BY-NC-ND",
        )

        if any(marker in name for marker in restricted_markers):
            return False

        if re.search(r"\bNC\b", name):
            return False

        return True

    async def search(
        self,
        query: str,
        orientation: Optional[str] = None,
        limit: int = 5,
    ) -> List[FootageCandidate]:

        ignored_words = {
            "bright",
            "modern",
            "enterprise",
            "footage",
            "real-world",
            "professional",
            "realistic",
            "b-roll",
        }

        clean_words = [
            word.strip(".,!?;:")
            for word in query.replace(",", " ").split()
            if len(word.strip(".,!?;:")) > 3
            and word.lower().strip(".,!?;:") not in ignored_words
        ][:3]

        search_term = (
            " ".join(clean_words)
            if clean_words
            else query.split()[0] if query.split() else "technology"
        )

        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:video {search_term}",
            "gsrnamespace": 6,
            "gsrlimit": min(max(limit, 1), 10),
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
        }

        headers = {"User-Agent": self.USER_AGENT}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self.API_URL,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

        except Exception as exc:
            logger.warning(
                f"Wikimedia Commons API query failed: {exc}"
            )
            return []

        pages = data.get("query", {}).get("pages", {})
        candidates: List[FootageCandidate] = []

        for page_id, page in pages.items():

            imageinfo = page.get("imageinfo", [])

            if not imageinfo:
                continue

            info = imageinfo[0]
            url = info.get("url")

            base_url = (
                url.split("?")[0].lower()
                if url
                else ""
            )

            if not base_url.endswith((".webm", ".mp4", ".ogv")):
                continue

            file_size = int(info.get("size", 0))

            if (
                file_size > self.MAX_FILE_SIZE
                or file_size < self.MIN_FILE_SIZE
            ):
                logger.info(
                    f"Skipping Wikimedia candidate {page_id}: "
                    f"file size {file_size} bytes"
                )
                continue

            metadata = info.get("extmetadata", {})

            # Never invent a licence when Wikimedia metadata is absent.
            license_short = self._clean_metadata(
                metadata.get("LicenseShortName", {}).get("value", "")
            )

            license_url = self._clean_metadata(
                metadata.get("LicenseUrl", {}).get("value", "")
            )

            if not self._is_commercially_usable_license(
                license_short,
                license_url,
            ):
                logger.info(
                    f"Rejected Wikimedia candidate {page_id}: "
                    f"missing or non-commercial licence metadata "
                    f"({license_short or 'unknown'})"
                )
                continue

            artist = self._clean_metadata(
                metadata.get("Artist", {}).get("value", "")
            )

            if not artist:
                artist = "Wikimedia contributor"

            width = int(info.get("width", 1920))
            height = int(info.get("height", 1080))

            if width <= 0 or height <= 0:
                continue

            if height > width:
                detected_orientation = "portrait"
            elif height == width:
                detected_orientation = "square"
            else:
                detected_orientation = "landscape"

            # Keep orientation as a preference rather than rejecting
            # every candidate that does not exactly match.
            # The renderer handles the requested output aspect ratio.
            if (
                orientation
                and orientation not in {
                    "portrait",
                    "landscape",
                    "square",
                }
            ):
                logger.warning(
                    f"Unknown requested orientation: {orientation}"
                )

            attribution = (
                f"File by {artist} via Wikimedia Commons "
                f"({license_short})"
            )

            candidates.append(
                FootageCandidate(
                    provider=self.name,
                    provider_asset_id=str(page_id),
                    preview_url=info.get("thumburl", url),
                    download_url=url,
                    source_url=info.get(
                        "descriptionurl",
                        f"https://commons.wikimedia.org/?curid={page_id}",
                    ),
                    licence_name=license_short,
                    licence_url=license_url,
                    attribution=attribution,
                    creator=artist[:200],
                    media_type="video",
                    duration=10.0,
                    width=width,
                    height=height,
                    orientation=detected_orientation,
                    is_ai_generated=False,
                    raw_metadata=info,
                )
            )

        # Prefer matching orientation, but retain other valid candidates
        # when there are not enough exact matches.
        if orientation in {"portrait", "landscape", "square"}:
            matching = [
                candidate
                for candidate in candidates
                if candidate.orientation == orientation
            ]

            if len(matching) >= min(2, limit):
                candidates = matching

        logger.info(
            f"Wikimedia Commons returned {len(candidates)} "
            f"candidates for '{query}'"
        )

        return candidates[:limit]

    async def download_clip(
        self,
        candidate: FootageCandidate,
        target_path: str,
    ) -> str:

        Path(target_path).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_file = target_path + ".tmp"

        headers = {
            "User-Agent": self.USER_AGENT
        }

        # Download original footage.
        try:
            async with httpx.AsyncClient(
                timeout=self.DOWNLOAD_TIMEOUT,
                follow_redirects=True,
            ) as client:

                response = await client.get(
                    candidate.download_url,
                    headers=headers,
                )

                response.raise_for_status()

        except Exception as exc:
            logger.exception(
                f"Wikimedia download failed for "
                f"{candidate.provider_asset_id}"
            )

            raise RuntimeError(
                f"Could not download Wikimedia footage: {exc}"
            ) from exc

        content = response.content

        content_type = response.headers.get(
            "content-type",
            "unknown",
        )

        logger.info(
            f"Wikimedia download received "
            f"{len(content)} bytes; "
            f"content-type={content_type}; "
            f"asset={candidate.provider_asset_id}"
        )

        if len(content) < self.MIN_FILE_SIZE:
            raise RuntimeError(
                f"Wikimedia returned an unexpectedly small file: "
                f"{len(content)} bytes"
            )

        # Save original download for processing.
        try:
            with open(temp_file, "wb") as file:
                file.write(content)

        except OSError as exc:
            raise RuntimeError(
                f"Could not save downloaded Wikimedia footage: {exc}"
            ) from exc

        # Memory-efficient normalization to H.264 MP4.
        #
        # Limit decoder threads, filter threads, output dimensions,
        # and encoder threads to avoid excessive memory consumption.
        scale_filter = (
            f"scale="
            f"w='min({self.MAX_OUTPUT_DIMENSION},iw)':"
            f"h='min({self.MAX_OUTPUT_DIMENSION},ih)':"
            f"force_original_aspect_ratio=decrease:"
            f"force_divisible_by=2"
        )

        cmd = [
            settings.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",

            # Limit decoder resource usage.
            "-threads",
            "1",

            "-filter_threads",
            "1",

            "-i",
            str(temp_file),

            "-t",
            str(self.MAX_CLIP_DURATION),

            "-map",
            "0:v:0",

            "-an",

            "-vf",
            scale_filter,

            "-c:v",
            "libx264",

            "-threads:v",
            str(self.MAX_ENCODER_THREADS),

            "-preset",
            "ultrafast",

            "-crf",
            "23",

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

            str(target_path),
        ]

        try:
            logger.info(
                f"Normalizing Wikimedia asset "
                f"{candidate.provider_asset_id} "
                f"with maximum dimensions "
                f"{self.MAX_OUTPUT_DIMENSION}x"
                f"{self.MAX_OUTPUT_DIMENSION}, "
                f"encoder threads={self.MAX_ENCODER_THREADS}"
            )

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=self.FFMPEG_TIMEOUT,
            )

            if result.returncode != 0:
                error_details = result.stderr or (
                    "FFmpeg returned a non-zero exit code "
                    "without diagnostic output."
                )

                logger.error(
                    f"Wikimedia FFmpeg conversion failed "
                    f"for asset {candidate.provider_asset_id}:\n"
                    f"{error_details}"
                )

                raise RuntimeError(
                    "Wikimedia FFmpeg conversion failed: "
                    f"{error_details[-3000:]}"
                )

            # Validate generated output.
            if not os.path.exists(target_path):
                raise RuntimeError(
                    "FFmpeg did not create the output video."
                )

            output_size = os.path.getsize(target_path)

            if output_size == 0:
                raise RuntimeError(
                    "FFmpeg generated an empty video file."
                )

            logger.info(
                f"Successfully normalized Wikimedia asset "
                f"{candidate.provider_asset_id}: "
                f"{output_size} bytes"
            )

            # Delete original only after successful conversion.
            os.remove(temp_file)

            return target_path

        except subprocess.TimeoutExpired as exc:
            logger.exception(
                f"FFmpeg timed out processing Wikimedia asset "
                f"{candidate.provider_asset_id}"
            )

            raise RuntimeError(
                "Wikimedia video conversion exceeded "
                f"{self.FFMPEG_TIMEOUT} seconds."
            ) from exc

        except Exception:
            logger.exception(
                f"Failed processing Wikimedia asset "
                f"{candidate.provider_asset_id}. "
                f"Original download retained at: {temp_file}"
            )

            # Preserve original download for debugging.
            raise
