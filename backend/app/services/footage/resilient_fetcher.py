from typing import Any, Dict, List, Optional, Tuple
from backend.app.config.settings import settings
from backend.app.core.errors import FootageNotFoundError
from backend.app.core.logging import logger
from backend.app.services.footage.local_pack import LocalLicensedFootageProvider
from backend.app.services.footage.mock_provider import MockFootageProvider
from backend.app.services.footage.models import FootageCandidate
from backend.app.services.footage.pexels_provider import PexelsProvider
from backend.app.services.footage.provider_base import FootageProvider
from backend.app.services.footage.wikimedia_provider import WikimediaCommonsProvider


class ResilientFootageFetcher:
    """
    Manages multi-provider footage acquisition, license verification,
    and automatic failover.
    Hierarchy: Pexels -> Wikimedia Commons -> Local Licensed Pack -> Mock (test only).
    """

    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.pexels = PexelsProvider()
        self.wikimedia = WikimediaCommonsProvider()
        self.local_pack = LocalLicensedFootageProvider()
        self.mock_provider = MockFootageProvider()

    async def get_candidates_for_query(
        self,
        query: str,
        orientation: Optional[str] = None,
        limit: int = 10,
    ) -> Tuple[List[FootageCandidate], List[str]]:
        """
        Queries available providers according to priority and returns valid,
        license-verified candidates along with logs of any fallbacks used.
        """
        if self.use_mock:
            candidates = await self.mock_provider.search(query, orientation=orientation, limit=limit)
            return candidates, ["mock_test_provider"]

        candidates: List[FootageCandidate] = []
        providers_tried: List[str] = []

        # 1. Primary: Pexels (if API key provided)
        if self.pexels.is_available:
            providers_tried.append(self.pexels.name)
            try:
                p_cands = await self.pexels.search(query, orientation=orientation, limit=limit)
                valid_p = [c for c in p_cands if self._verify_candidate_license(c)]
                candidates.extend(valid_p)
            except Exception as e:
                logger.warning(f"Primary provider Pexels error ({e}); will try fallbacks.")

        # 2. Secondary: Wikimedia Commons (commercial CC0/CC-BY)
        if len(candidates) < 3:
            providers_tried.append(self.wikimedia.name)
            try:
                w_cands = await self.wikimedia.search(query, orientation=orientation, limit=limit)
                valid_w = [c for c in w_cands if self._verify_candidate_license(c)]
                candidates.extend(valid_w)
            except Exception as e:
                logger.warning(f"Secondary provider Wikimedia error ({e}); proceeding to local pack.")

        # 3. Tertiary: Local Verified Licensed Pack
        if len(candidates) < 2:
            providers_tried.append(self.local_pack.name)
            try:
                l_cands = await self.local_pack.search(query, orientation=orientation, limit=limit)
                valid_l = [c for c in l_cands if self._verify_candidate_license(c)]
                candidates.extend(valid_l)
            except Exception as e:
                logger.error(f"Local licensed pack search failed ({e})")

        return candidates, providers_tried

    def _verify_candidate_license(self, candidate: FootageCandidate) -> bool:
        """
        Enforces strict licensing rules:
        - Must have a verifiable license name and license URL.
        - Must not be non-commercial (NC).
        - Must have valid attribution information.
        """
        if not candidate.licence_name or not candidate.licence_url:
            logger.warning(f"Candidate {candidate.provider_asset_id} rejected: missing license information")
            return False

        lic_upper = candidate.licence_name.upper()
        if "NC" in lic_upper or "NON-COMMERCIAL" in lic_upper or "NONCOMMERCIAL" in lic_upper:
            logger.warning(f"Candidate {candidate.provider_asset_id} rejected: non-commercial license ({candidate.licence_name})")
            return False

        if not candidate.source_url:
            logger.warning(f"Candidate {candidate.provider_asset_id} rejected: missing source URL")
            return False

        return True

    async def download_selected_candidate(self, candidate: FootageCandidate, target_path: str) -> str:
        provider_name = candidate.provider
        if provider_name == self.pexels.name:
            return await self.pexels.download_clip(candidate, target_path)
        elif provider_name == self.wikimedia.name:
            return await self.wikimedia.download_clip(candidate, target_path)
        elif provider_name == self.local_pack.name:
            return await self.local_pack.download_clip(candidate, target_path)
        else:
            return await self.mock_provider.download_clip(candidate, target_path)
