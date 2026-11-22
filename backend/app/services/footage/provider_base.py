from abc import ABC, abstractmethod
from typing import List, Optional
from backend.app.services.footage.models import FootageCandidate


class FootageProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider machine name (e.g. 'pexels', 'local_pack', 'mock')."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Indicates if the provider has valid credentials and connectivity."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        orientation: Optional[str] = None,
        limit: int = 10,
    ) -> List[FootageCandidate]:
        """Searches provider for footage matching query."""
        pass

    @abstractmethod
    async def download_clip(self, candidate: FootageCandidate, target_path: str) -> str:
        """Downloads the selected candidate clip to local storage and returns local path."""
        pass
