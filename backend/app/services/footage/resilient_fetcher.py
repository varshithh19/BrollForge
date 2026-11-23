
from typing import List, Optional, Tuple

from backend.app.core.errors import FootageNotFoundError
from backend.app.core.logging import logger
from backend.app.services.footage.mock_provider import MockFootageProvider
from backend.app.services.footage.models import FootageCandidate
from backend.app.services.footage.pexels_provider import PexelsProvider
from backend.app.services.footage.wikimedia_provider import WikimediaCommonsProvider


class ResilientFootageFetcher:
    """
    Manages footage acquisition and basic license metadata checks.

    Production hierarchy:
        Pexels -> Wikimedia Commons

    Mock footage is available only when explicitly enabled for testing.
    Synthetic local test patterns are never used as licensed stock footage.
    """

    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.pexels = PexelsProvider()
        self.wikimedia = WikimediaCommonsProvider()
        self.mock_provider = MockFootageProvider()

    async def get_candidates_for_query(
        self,
        query: str,
        orientation: Optional[str] = None,
        limit: int = 10,
    ) -> Tuple[List[FootageCandidate], List[str]]:

        if self.use_mock:
            candidates = await self.mock_provider.search(
                query,
                orientation=orientation,
                limit=limit,
            )
            return candidates, ["mock_test_provider"]

        candidates: List[FootageCandidate] = []
        providers_tried: List[str] = []

        # 1. Primary provider: Pexels
        if self.pexels.is_available:
            providers_tried.append(self.pexels.name)

            try:
                pexels_candidates = await self.pexels.search(
                    query,
                    orientation=orientation,
                    limit=limit,
                )

                valid_candidates = [
                    candidate
                    for candidate in pexels_candidates
                    if self._verify_candidate_license(candidate)
                ]

                candidates.extend(valid_candidates)

            except Exception as exc:
                logger.warning(
                    f"Pexels search failed; trying Wikimedia Commons: {exc}"
                )

        # 2. Secondary provider: Wikimedia Commons
        if len(candidates) < 3:
            providers_tried.append(self.wikimedia.name)

            try:
                wikimedia_candidates = await self.wikimedia.search(
                    query,
                    orientation=orientation,
                    limit=limit,
                )

                valid_candidates = [
                    candidate
                    for candidate in wikimedia_candidates
                    if self._verify_candidate_license(candidate)
                ]

                candidates.extend(valid_candidates)

            except Exception as exc:
                logger.warning(
                    f"Wikimedia Commons search failed: {exc}"
                )

        # Do not silently substitute synthetic or mock footage.
        if not candidates:
            logger.warning(
                f"No eligible footage found for query: {query}"
            )

        return candidates, providers_tried

    def _verify_candidate_license(
        self,
        candidate: FootageCandidate,
    ) -> bool:
        """
        Performs basic metadata checks.

        Note: These checks do not independently establish ownership,
        authenticity, or legal validity of a license.
        """

        if not candidate.licence_name or not candidate.licence_url:
            logger.warning(
                f"Rejected {candidate.provider_asset_id}: missing license metadata"
            )
            return False

        license_name = candidate.licence_name.upper()

        if (
            "NON-COMMERCIAL" in license_name
            or "NONCOMMERCIAL" in license_name
            or " CC NC" in license_name
            or license_name.endswith("NC")
        ):
            logger.warning(
                f"Rejected {candidate.provider_asset_id}: "
                f"non-commercial license"
            )
            return False

        if not candidate.source_url:
            logger.warning(
                f"Rejected {candidate.provider_asset_id}: missing source URL"
            )
            return False

        return True

    async def download_selected_candidate(
        self,
        candidate: FootageCandidate,
        target_path: str,
    ) -> str:

        provider_name = candidate.provider

        if provider_name == self.pexels.name:
            return await self.pexels.download_clip(
                candidate,
                target_path,
            )

        if provider_name == self.wikimedia.name:
            return await self.wikimedia.download_clip(
                candidate,
                target_path,
            )

        if self.use_mock and provider_name == self.mock_provider.name:
            return await self.mock_provider.download_clip(
                candidate,
                target_path,
            )

        raise FootageNotFoundError(
            f"Unsupported or disabled footage provider: {provider_name}"
        )
