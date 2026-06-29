from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit


@dataclass
class PostData:
    site: str
    post_type: str
    post_id: str | int | None = None
    media: list[list[str]] = field(default_factory=list)
    text: str = ""
    author: str = ""
    url: str = ""
    spoiler: bool = False
    poll: bool = False
    reply: bool = False
    quote: bool = False
    reply_url: str = ""
    quote_url: str = ""
    community_note: bool = False
    community_note_text: str = ""
    community_note_links: list[dict[str, Any]] = field(default_factory=list)


class MediaHandler(ABC):
    SITE_NAME = "unknown"
    enabled = True

    def normalize_url(self, link: str) -> str:
        parsed = urlsplit(link)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))

    @abstractmethod
    def handle(self, link: str) -> PostData | None:
        pass

    # Optional hook for handlers that can provide a fallback embed link.
    # Returns a PostData to send as the fallback, or None if no fallback is available.
    def handle_fallback(self, link: str) -> PostData | None:
        return None
