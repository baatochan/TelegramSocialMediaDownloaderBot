import re
import time

from telebot.formatting import escape_markdown
from telebot.types import (InputMediaPhoto, InputMediaVideo,
                           LinkPreviewOptions, ReplyParameters)

import file_downloader
from handlers.base import PostData


class Caption:
    def __init__(self, short, long):
        self.short = short
        self.long = long


class PostDataSender:
    def __init__(self, bot, error_message: str):
        self.bot = bot
        self.error_message = error_message

    def send(self, orig_tg_msg, post_data: PostData, msg_to_reply_to=None, caption_suffix=""):
        caption = self.prepare_caption(post_data)
        if msg_to_reply_to is None:
            msg_to_reply_to = orig_tg_msg

        if caption_suffix:
            caption.long += caption_suffix

        match (post_data.post_type):
            case "media":
                return self.send_media_post(orig_tg_msg, post_data, caption, msg_to_reply_to)
            case "text":
                return self.send_text_post(orig_tg_msg, caption, msg_to_reply_to)
            case _:
                return self.bot.reply_to(msg_to_reply_to, self.error_message)

    def prepare_caption(self, post_data: PostData):
        long_caption = ""
        short_caption = ""
        if post_data.text:
            post_data.text = self.remove_hashtags(post_data.text)
            long_caption += post_data.text
        if post_data.author:
            long_caption += "\n\nby: " + post_data.author
            short_caption += "by: " + post_data.author
        if post_data.url:
            long_caption += "\n" + post_data.url
            short_caption += "\n" + post_data.url
        long_caption = escape_markdown(long_caption)
        short_caption = escape_markdown(short_caption)

        if post_data.poll:
            long_caption = "*This post is a poll\!*\n\n" + long_caption

        if post_data.site == "twitter" and post_data.community_note:
            long_caption += self.parse_community_notes(post_data)

        return Caption(short_caption, long_caption)

    def remove_hashtags(self, text):
        # Remove hashtags when there are 4 or more grouped together
        # # and eveyrthing not being a whitespace is considered a signle hashtag
        text = re.sub(r'((#[^\s]+)\s+){3,}(#[^\s]+)', '', text, flags=re.UNICODE)
        # Removing hashtags may leave some empty lines so we need to remove them
        text = text.strip()
        return text

    def parse_community_notes(self, post_data: PostData):
        if not post_data.community_note_links:
            return "\n\n*This tweet has community notes*:\n" + escape_markdown(post_data.community_note_text)

        note_arr = []
        split_indices = []
        links = []
        text = post_data.community_note_text

        split_indices.append(0)
        for link in post_data.community_note_links:
            split_indices.append(link['from'])
            split_indices.append(link['to'])
            links.append(link['url'])
        split_indices.append(None)

        link_index = 0
        for i in range(len(split_indices) - 1):
            is_link = i % 2 == 1
            if not is_link:
                note_arr.append(
                    {"text": text[split_indices[i]:split_indices[i+1]], "is_link": is_link})
            else:
                note_arr.append({"text": text[split_indices[i]:split_indices[i+1]],
                                "is_link": is_link, "link": links[link_index]})
                link_index += 1

        note = "\n\n*This tweet has community notes*:\n"
        for note_part in note_arr:
            if note_part["is_link"]:
                note += "[" + escape_markdown(note_part["text"]) + \
                    "](" + note_part["link"] + ")"
            else:
                note += escape_markdown(note_part["text"])

        return note

    def send_media_post(self, orig_tg_msg, post_data: PostData, caption, msg_to_reply_to):
        if len(post_data.media) == 1:
            return self.send_singular_media_post(
                orig_tg_msg, post_data, caption, msg_to_reply_to)
        else:
            return self.send_multiple_media_post(
                orig_tg_msg, post_data, caption, msg_to_reply_to)

    def send_singular_media_post(self, orig_tg_msg, post_data: PostData, caption, msg_to_reply_to):
        media = post_data.media[0]
        if media[1] == "photo":
            sent_message = self.send_photo_post(
                orig_tg_msg, media[0], caption, post_data.spoiler, msg_to_reply_to)
        elif media[1] == "video":
            sent_message = self.send_video_post(
                orig_tg_msg, media[0], caption, post_data.spoiler, msg_to_reply_to)
        elif media[1] == "video_file":
            video_file = open(media[0], "rb")
            sent_message = self.send_video_post(
                orig_tg_msg, video_file, caption, post_data.spoiler, msg_to_reply_to)
        elif media[1] == "gif":
            sent_message = self.send_gif_post(
                orig_tg_msg, media[0], caption, post_data.spoiler, msg_to_reply_to)
        else:
            print("This type of media (" + media[1] + ") is not supported.")
            print(post_data)
            return orig_tg_msg

        self.delete_handled_message(orig_tg_msg)
        return sent_message

    def send_photo_post(self, orig_tg_msg, photo, caption, has_spoiler, msg_to_reply_to):
        if len(caption.long) <= 1024:
            sent_message = self.bot.send_photo(chat_id=orig_tg_msg.chat.id,
                                               photo=photo,
                                               caption=caption.long,
                                               has_spoiler=has_spoiler,
                                               reply_parameters=ReplyParameters(
                                                   message_id=msg_to_reply_to.message_id,
                                                   allow_sending_without_reply=True))
        else:
            # TODO: secure for over 4096 characters
            sent_message = self.bot.send_photo(chat_id=orig_tg_msg.chat.id,
                                               photo=photo,
                                               caption=caption.short,
                                               has_spoiler=has_spoiler,
                                               reply_parameters=ReplyParameters(
                                                   message_id=msg_to_reply_to.message_id,
                                                   allow_sending_without_reply=True))
            sent_message = self.bot.send_message(chat_id=orig_tg_msg.chat.id,
                                                 text=caption.long,
                                                 reply_parameters=ReplyParameters(
                                                     message_id=sent_message.message_id),
                                                 link_preview_options=LinkPreviewOptions(is_disabled=True))
        return sent_message

    def send_video_post(self, orig_tg_msg, video, caption, has_spoiler, msg_to_reply_to):
        if len(caption.long) <= 1024:
            sent_message = self.bot.send_video(chat_id=orig_tg_msg.chat.id,
                                               video=video,
                                               caption=caption.long,
                                               has_spoiler=has_spoiler,
                                               reply_parameters=ReplyParameters(
                                                   message_id=msg_to_reply_to.message_id,
                                                   allow_sending_without_reply=True))
        else:
            # TODO: secure for over 4096 characters
            sent_message = self.bot.send_video(chat_id=orig_tg_msg.chat.id,
                                               video=video,
                                               caption=caption.short,
                                               has_spoiler=has_spoiler,
                                               reply_parameters=ReplyParameters(
                                                   message_id=msg_to_reply_to.message_id,
                                                   allow_sending_without_reply=True))
            sent_message = self.bot.send_message(chat_id=orig_tg_msg.chat.id,
                                                 text=caption.long,
                                                 reply_parameters=ReplyParameters(
                                                     message_id=sent_message.message_id),
                                                 link_preview_options=LinkPreviewOptions(is_disabled=True))
        return sent_message

    def send_gif_post(self, orig_tg_msg, gif, caption, has_spoiler, msg_to_reply_to):
        if len(caption.long) <= 1024:
            sent_message = self.bot.send_animation(chat_id=orig_tg_msg.chat.id,
                                                   animation=gif,
                                                   caption=caption.long,
                                                   has_spoiler=has_spoiler,
                                                   reply_parameters=ReplyParameters(
                                                       message_id=msg_to_reply_to.message_id,
                                                       allow_sending_without_reply=True))
        else:
            # TODO: secure for over 4096 characters
            sent_message = self.bot.send_animation(chat_id=orig_tg_msg.chat.id,
                                                   animation=gif,
                                                   caption=caption.short,
                                                   has_spoiler=has_spoiler,
                                                   reply_parameters=ReplyParameters(
                                                       message_id=msg_to_reply_to.message_id,
                                                       allow_sending_without_reply=True))
            sent_message = self.bot.send_message(chat_id=orig_tg_msg.chat.id,
                                                 text=caption.long,
                                                 reply_parameters=ReplyParameters(
                                                     message_id=sent_message.message_id),
                                                 link_preview_options=LinkPreviewOptions(is_disabled=True))
        return sent_message

    def send_multiple_media_post(self, orig_tg_msg, post_data: PostData, caption, msg_to_reply_to):
        media_group = []
        i = 0
        for media in post_data.media:
            if media[1] == "photo":
                media_group.append(InputMediaPhoto(
                    media=media[0], has_spoiler=post_data.spoiler))
            elif media[1] == "video":
                media_group.append(InputMediaVideo(
                    media=media[0], has_spoiler=post_data.spoiler))
            elif media[1] == "video_file":
                media_group.append(InputMediaVideo(
                    media=open(media[0], "rb"), has_spoiler=post_data.spoiler))
            elif media[1] == "gif":
                filename = file_downloader.download_video(
                    media[0], post_data.site, str(post_data.post_id) + "_" + str(i))
                i += 1
                media_group.append(InputMediaVideo(
                    media=open(filename, "rb"), has_spoiler=post_data.spoiler))
            else:
                print("This type of media (" + media[1] + ") is not supported.")
                print(post_data)

        if len(media_group) > 10:
            # media post in tg can have at most 10 media
            self.send_split_multiple_media_post(
                orig_tg_msg, media_group, caption, msg_to_reply_to)
        elif len(media_group) > 0:
            if len(caption.long) <= 1024:
                media_group[0].caption = caption.long
                sent_message_arr = self.bot.send_media_group(chat_id=orig_tg_msg.chat.id,
                                                             media=media_group,
                                                             reply_parameters=ReplyParameters(
                                                                 message_id=msg_to_reply_to.message_id,
                                                                 allow_sending_without_reply=True))

                self.delete_handled_message(orig_tg_msg)
                # send_media_group returns an array of msgs, we need just the first one
                return sent_message_arr[0]
            else:
                # TODO: secure for over 4096 characters
                media_group[0].caption = caption.short
                sent_message_arr = self.bot.send_media_group(chat_id=orig_tg_msg.chat.id,
                                                             media=media_group,
                                                             reply_parameters=ReplyParameters(
                                                                 message_id=msg_to_reply_to.message_id,
                                                                 allow_sending_without_reply=True))
                sent_message_with_caption = self.bot.send_message(chat_id=orig_tg_msg.chat.id,
                                                                  text=caption.long,
                                                                  reply_parameters=ReplyParameters(
                                                                      message_id=sent_message_arr[0].message_id),
                                                                  link_preview_options=LinkPreviewOptions(is_disabled=True))
                self.delete_handled_message(orig_tg_msg)
                return sent_message_with_caption
        else:
            print("Multi media post doesn't contain any supported media.")
            print(post_data)
            return orig_tg_msg

    def send_split_multiple_media_post(self, orig_tg_msg, media_group, caption, msg_to_reply_to):
        # split media_group into chunks of 10 elements
        chunk_size = 10
        media_groups = [media_group[i:i + chunk_size]
                        for i in range(0, len(media_group), 10)]
        for i in range(len(media_groups)):
            media_groups[i][0].caption = caption.short
            sent_message_arr = self.bot.send_media_group(chat_id=orig_tg_msg.chat.id,
                                                         media=media_groups[i],
                                                         reply_parameters=ReplyParameters(
                                                             message_id=msg_to_reply_to.message_id,
                                                             allow_sending_without_reply=True))
            # next msg shall reply to the previous one
            msg_to_reply_to = sent_message_arr[0]

        sent_message_with_caption = self.bot.send_message(chat_id=orig_tg_msg.chat.id,
                                                          text=caption.long,
                                                          reply_parameters=ReplyParameters(
                                                              message_id=msg_to_reply_to.message_id),
                                                          link_preview_options=LinkPreviewOptions(is_disabled=True))

        self.delete_handled_message(orig_tg_msg)
        return sent_message_with_caption

    def send_text_post(self, orig_tg_msg, caption, msg_to_reply_to):
        sent_message = self.bot.send_message(chat_id=orig_tg_msg.chat.id,
                                            text=caption.long,
                                            reply_parameters=ReplyParameters(
                                                message_id=msg_to_reply_to.message_id,
                                                allow_sending_without_reply=True),
                                            link_preview_options=LinkPreviewOptions(is_disabled=True))
        self.delete_handled_message(orig_tg_msg)
        return sent_message

    def delete_handled_message(self, message):
        try:
            self.bot.delete_message(message.chat.id, message.id)
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            print(str(e))
            print("Cant remove message in chat " +
                  str(message.chat.title) + " (" + str(message.chat.id) + ").")
            print()
