from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


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

    def to_legacy_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "site": self.site,
            "type": self.post_type,
        }

        if self.post_id is not None:
            data["id"] = self.post_id
        if self.media:
            data["media"] = self.media
        if self.text:
            data["text"] = self.text
        if self.author:
            data["author"] = self.author
        if self.url:
            data["url"] = self.url

        data["spoiler"] = self.spoiler
        data["poll"] = self.poll
        data["reply"] = self.reply
        data["quote"] = self.quote

        if self.reply_url:
            data["reply_url"] = self.reply_url
        if self.quote_url:
            data["quote_url"] = self.quote_url

        data["community_note"] = self.community_note
        if self.community_note_text:
            data["community_note_text"] = self.community_note_text
        if self.community_note_links:
            data["community_note_links"] = self.community_note_links

        return data


class MediaHandler(ABC):
    @abstractmethod
    def handle(self, link: str) -> PostData | None:
        pass

    # Optional hook for handlers that can send fallback embed links.
    def handle_fallback(self, tg_message, link: str) -> None:
        return None
