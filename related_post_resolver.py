from dataclasses import dataclass
from enum import Enum

from telebot.formatting import escape_markdown

from handlers.base import MediaHandler, PostData
from post_data_sender import PostDataSender


class RelatedPostKind(Enum):
    QUOTE = "quote"
    REPLY = "reply"


@dataclass(frozen=True)
class RelatedPostRef:
    kind: RelatedPostKind
    url: str
    resolve: bool


class RelatedPostResolver:
    def __init__(self, post_data_sender: PostDataSender):
        self.post_data_sender = post_data_sender

    def prepare_send_context(self, orig_tg_msg, post_data: PostData, handler: MediaHandler,
                             *, skip_resolution: bool):
        visited: set[str] = set()
        msg_to_reply_to, caption_suffix = self._prepare_send_context(
            orig_tg_msg,
            post_data,
            handler,
            skip_resolution=skip_resolution,
            msg_to_reply_to=orig_tg_msg,
            caption_suffix="",
            visited=visited,
        )
        return msg_to_reply_to, caption_suffix

    def _build_plan(self, post_data: PostData, skip_resolution: bool) -> list[RelatedPostRef]:
        refs: list[RelatedPostRef] = []

        if post_data.quote and post_data.quote_url:
            resolve = not skip_resolution and not post_data.reply
            refs.append(RelatedPostRef(RelatedPostKind.QUOTE, post_data.quote_url, resolve))

        if post_data.reply and post_data.reply_url:
            resolve = not skip_resolution
            refs.append(RelatedPostRef(RelatedPostKind.REPLY, post_data.reply_url, resolve))

        return refs

    def _prepare_send_context(self, orig_tg_msg, post_data: PostData, handler: MediaHandler,
                              *, skip_resolution: bool, msg_to_reply_to, caption_suffix: str,
                              visited: set[str]):
        for ref in self._build_plan(post_data, skip_resolution):
            if ref.resolve:
                msg_to_reply_to, caption_suffix = self._resolve_and_send_related(
                    orig_tg_msg,
                    ref,
                    handler,
                    msg_to_reply_to,
                    caption_suffix,
                    visited,
                )
            else:
                caption_suffix = self._add_caption_note(caption_suffix, ref)

        return msg_to_reply_to, caption_suffix

    def _resolve_and_send_related(self, orig_tg_msg, ref: RelatedPostRef, handler: MediaHandler,
                                  msg_to_reply_to, caption_suffix: str, visited: set[str]):
        normalized_url = handler.normalize_url(ref.url)

        if normalized_url in visited:
            return msg_to_reply_to, self._add_caption_note(caption_suffix, ref)

        visited.add(normalized_url)

        related_post_data = handler.handle(normalized_url)
        if related_post_data is None:
            print("Can't handle related " + ref.kind.value + " link: " + ref.url)
            return msg_to_reply_to, self._add_caption_note(caption_suffix, ref)

        related_msg_to_reply_to, related_caption_suffix = self._prepare_send_context(
            orig_tg_msg,
            related_post_data,
            handler,
            skip_resolution=False,
            msg_to_reply_to=orig_tg_msg,
            caption_suffix="",
            visited=visited,
        )
        msg_to_reply_to = self.post_data_sender.send(
            orig_tg_msg,
            related_post_data,
            msg_to_reply_to=related_msg_to_reply_to,
            caption_suffix=related_caption_suffix,
        )

        return msg_to_reply_to, caption_suffix

    def _add_caption_note(self, caption_suffix: str, ref: RelatedPostRef) -> str:
        if ref.kind == RelatedPostKind.QUOTE:
            note = "\n\n*Note:* This post is a quote repost of: " + escape_markdown(ref.url)
        else:
            note = "\n\n*Note:* This post is a reply to: " + escape_markdown(ref.url)

        return caption_suffix + note
