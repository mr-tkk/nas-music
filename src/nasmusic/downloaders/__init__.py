from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from nasmusic.core.models import SearchResult, DownloadResult, TrackMetadata


class BaseDownloader(ABC):
    source_name: str = "unknown"

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        ...

    @abstractmethod
    def download(self, identifier: str, output_dir) -> DownloadResult:
        ...

    def get_metadata(self, identifier: str) -> Optional[TrackMetadata]:
        return None
