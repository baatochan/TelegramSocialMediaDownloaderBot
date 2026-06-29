from dataclasses import dataclass
from enum import Enum

from telebot.formatting import escape_markdown

from handlers.base import MediaHandler, PostData


class RelatedPostKind(Enum):
    QUOTE = "quote"
    REPLY = "reply"


@dataclass(frozen=True)
class RelatedPostRef:
    kind: RelatedPostKind
    url: str
    resolve: bool


@dataclass
class ResolvedPost:
    post_data: PostData
    caption_suffix: str = ""


class RelatedPostResolver:
    def resolve(self, post_data: PostData, handler: MediaHandler, *, skip_resolution: bool) -> list[ResolvedPost]:
        visited: set[str] = set()
        main_caption_suffix, ancestor_chain = self._fetch_ancestors(
            post_data,
            handler,
            skip_resolution=skip_resolution,
            visited=visited,
        )

        posts = list(reversed(ancestor_chain))
        posts.append(ResolvedPost(post_data, main_caption_suffix))
        return posts

    def _build_plan(self, post_data: PostData, skip_resolution: bool) -> list[RelatedPostRef]:
        refs: list[RelatedPostRef] = []

        if post_data.quote and post_data.quote_url:
            resolve = not skip_resolution and not post_data.reply
            refs.append(RelatedPostRef(RelatedPostKind.QUOTE, post_data.quote_url, resolve))

        if post_data.reply and post_data.reply_url:
            resolve = not skip_resolution
            refs.append(RelatedPostRef(RelatedPostKind.REPLY, post_data.reply_url, resolve))

        return refs

    def _fetch_ancestors(self, post_data: PostData, handler: MediaHandler, *, skip_resolution: bool,
                         visited: set[str]) -> tuple[str, list[ResolvedPost]]:
        caption_suffix = ""
        chain: list[ResolvedPost] = []

        for ref in self._build_plan(post_data, skip_resolution):
            if not ref.resolve:
                caption_suffix = self._add_caption_note(caption_suffix, ref)
                continue

            normalized_url = handler.normalize_url(ref.url)

            if normalized_url in visited:
                caption_suffix = self._add_caption_note(caption_suffix, ref)
                continue

            visited.add(normalized_url)

            related_post_data = handler.handle(normalized_url)
            if related_post_data is None:
                print("Can't handle related " + ref.kind.value + " link: " + ref.url)
                caption_suffix = self._add_caption_note(caption_suffix, ref)
                continue

            nested_caption_suffix, deeper_chain = self._fetch_ancestors(
                related_post_data,
                handler,
                skip_resolution=False,
                visited=visited,
            )
            chain = [ResolvedPost(related_post_data, nested_caption_suffix)] + deeper_chain

        return caption_suffix, chain

    def _add_caption_note(self, caption_suffix: str, ref: RelatedPostRef) -> str:
        if ref.kind == RelatedPostKind.QUOTE:
            note = "\n\n*Note:* This post is a quote repost of: " + escape_markdown(ref.url)
        else:
            note = "\n\n*Note:* This post is a reply to: " + escape_markdown(ref.url)

        return caption_suffix + note
