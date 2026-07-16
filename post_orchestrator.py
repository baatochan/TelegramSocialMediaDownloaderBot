import time
import traceback


class PostOrchestrator:
    def __init__(self, post_data_sender, related_post_resolver, allowed_chats):
        self.post_data_sender = post_data_sender
        self.related_post_resolver = related_post_resolver
        self.allowed_chats = allowed_chats

    def send_post_with_fallback(self, message, post_data, handler, link_to_handle) -> None:
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
