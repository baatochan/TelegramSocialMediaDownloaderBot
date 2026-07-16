import time
import traceback

from post_handling_policies import DescriptionPolicy, PostHandlingPolicies, SpoilerPolicy


class PostOrchestrator:
    def __init__(self, post_data_sender, related_post_resolver, allowed_chats):
        self.post_data_sender = post_data_sender
        self.related_post_resolver = related_post_resolver
        self.allowed_chats = allowed_chats

    def process_link_for_handler(self, message, link: str, handler,
                                 post_handling_policies: PostHandlingPolicies) -> None:
        site_label = handler.SITE_NAME
        link_to_handle = handler.normalize_url(link)

        post_data = handler.handle(link_to_handle)
        if post_data is None:
            print("Can't handle " + site_label + " link: " + str(link))

            post_data = handler.handle_fallback(link_to_handle)
            if post_data is None:
                return

        self._apply_policies(post_data, post_handling_policies)

        self._send_chain_with_fallback(
            message,
            post_data,
            handler,
            link_to_handle,
        )

    def _apply_policies(self, post_data,
                        post_handling_policies: PostHandlingPolicies) -> None:
        if post_handling_policies.spoiler_policy == SpoilerPolicy.FORCE_SPOILER:
            post_data.spoiler = True
        elif post_handling_policies.spoiler_policy == SpoilerPolicy.FORCE_NO_SPOILER:
            post_data.spoiler = False

        if post_handling_policies.description_policy == DescriptionPolicy.REMOVE_DESCRIPTION:
            post_data.text = ""

    def _send_chain_with_fallback(self, message, post_data, handler, link_to_handle) -> None:
        try:
            chain = self.related_post_resolver.resolve(
                post_data,
                handler,
                skip_resolution=message.chat.id in self.allowed_chats,
            )
            msg_to_reply_to = message
            for entry in chain:
                msg_to_reply_to = self.post_data_sender.send(
                    message,
                    entry.post_data,
                    msg_to_reply_to=msg_to_reply_to,
                    caption_suffix=entry.caption_suffix,
                )
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            traceback.print_exception(type(e), e, e.__traceback__)
            print()
            print("Couldn't send " + handler.SITE_NAME +
                  " post, trying fallback: " + str(link_to_handle))

            fallback_post_data = handler.handle_fallback(link_to_handle)
            if fallback_post_data is None:
                return

            self.post_data_sender.send(message, fallback_post_data)
