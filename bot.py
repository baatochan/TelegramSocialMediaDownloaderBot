#!/usr/bin/env python3
import configparser
import json
import os
import re
import signal
import sys
import time
import traceback
from enum import Enum

import telebot
from telebot.formatting import escape_markdown
from telebot.types import (InputMediaPhoto, InputMediaVideo,
                           LinkPreviewOptions, ReplyParameters)
from tendo import singleton

from handlers.booru_handler import BooruHandler
from handlers.demoty_handler import DemotyHandler
from handlers.instagram_handler import InstagramHandler
from handlers.ninegag_handler import NineGagHandler
from handlers.tiktok_handler import TikTokHandler
from handlers.twitter_handler import TwitterHandler
from handlers.youtube_handler import YouTubeHandler
import file_downloader


class Caption:
    def __init__(self, short, long):
        self.short = short
        self.long = long


class OverrideSpoiler(Enum):
    NO_OVERRIDE = 0
    SPOILER = 1
    NO_SPOILER = 2


me = singleton.SingleInstance()  # will sys.exit(-1) if other instance is running

config = configparser.ConfigParser()
if os.path.isfile("config.txt"):
    config.read("config.txt")
else:
    print("No config file. Create config file and run the script again.")
    exit(1)

ALLOWED_USERS = json.loads(config['config']['allowed_users'])
ALLOWED_CHATS = json.loads(config['config']['allowed_chats'])

YOUTUBE_SUPPORT_ENABLED = config['youtube'].getboolean('enabled')

bot = telebot.TeleBot(config['config']['token'])
BOT_ID = bot.get_me().id
PARSE_MODE = "MarkdownV2"
bot.parse_mode = PARSE_MODE

ERROR_MESSAGE = escape_markdown("Can't download this post. Try again later.")

booru_handler = BooruHandler()
instagram_handler = InstagramHandler.create_from_config(config['instagram'])
ninegag_handler = NineGagHandler(
    use_selenium=config['9gag'].getboolean('use_selenium'))
tiktok_handler = TikTokHandler()
twitter_handler = TwitterHandler()
demoty_handler = DemotyHandler()
youtube_handler = YouTubeHandler()


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.from_user.id in ALLOWED_USERS:
        welcome_message_text = escape_markdown("Hi, I can download media from different social media and send" +
                                               " them to you here on telegram. Send me a link and I'll take care of the rest.")
        bot.reply_to(message=message, text=welcome_message_text)
    else:
        print(message.from_user)
        unwelcome_message_text = escape_markdown("Hi, only approved users can use me. Contact " +
                                                 config['config']['owner_username'] +
                                                 " if you think you should get the access :)")
        bot.reply_to(message=message,
                     text=unwelcome_message_text,
                     parse_mode=None)


@bot.message_handler(regexp=ninegag_handler.URL_REGEX, func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
@bot.message_handler(regexp=twitter_handler.URL_REGEX, func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
@bot.message_handler(regexp=instagram_handler.URL_REGEX, func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
@bot.message_handler(regexp=booru_handler.URL_REGEX, func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
@bot.message_handler(regexp=demoty_handler.URL_REGEX, func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
@bot.message_handler(regexp=tiktok_handler.URL_REGEX, func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
@bot.message_handler(regexp=youtube_handler.URL_REGEX, func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
def handle_supported_site(message):
    if message.forward_origin and message.forward_origin.type == "user" and message.forward_origin.sender_user.id == BOT_ID:
        return

    overrideSpoiler = OverrideSpoiler.NO_OVERRIDE
    if "BBspoiler=True" in message.text:
        overrideSpoiler = OverrideSpoiler.SPOILER
    elif "BBspoiler=False" in message.text:
        overrideSpoiler = OverrideSpoiler.NO_SPOILER

    removeDescription = False
    if "BBnoDesc=True" in message.text:
        removeDescription = True

    msgContent = message.text.split()

    r = re.compile(ninegag_handler.URL_REGEX)
    ninegagLinks = list(filter(r.match, msgContent))
    for link in ninegagLinks:
        link = link.split("?")  # we don't need parameters after ?
        post_data = ninegag_handler.handle(link[0])
        if post_data is not None:
            handler_response = post_data.to_legacy_dict()
            if overrideSpoiler != OverrideSpoiler.NO_OVERRIDE:
                handler_response['spoiler'] = overrideSpoiler == OverrideSpoiler.SPOILER
            if removeDescription:
                handler_response['text'] = ""
            send_post_to_tg(message, handler_response)
        else:
            print("Can't handle 9gag link: ")
            print(*link, sep="?")

    r = re.compile(twitter_handler.URL_REGEX)
    twitterLinks = list(filter(r.match, msgContent))
    for link in twitterLinks:
        link = link.split("?")  # we don't need parameters after ?
        post_data = twitter_handler.handle(link[0])
        if post_data is not None:
            handler_response = post_data.to_legacy_dict()
            if overrideSpoiler != OverrideSpoiler.NO_OVERRIDE:
                handler_response['spoiler'] = overrideSpoiler == OverrideSpoiler.SPOILER
            if removeDescription:
                handler_response['text'] = ""
            msg_to_reply_to, caption_suffix = prepare_twitter_send_context(
                message, handler_response)
            send_post_to_tg(
                message,
                handler_response,
                msg_to_reply_to=msg_to_reply_to,
                caption_suffix=caption_suffix,
            )
        else:
            print("Can't handle twitter link: ")
            print(*link, sep="?")

    r = re.compile(instagram_handler.URL_REGEX)
    igLinks = list(filter(r.match, msgContent))
    for link in igLinks:
        link = link.split("?")  # we don't need parameters after ?
        post_data = instagram_handler.handle(link[0])
        if post_data is not None:
            handler_response = post_data.to_legacy_dict()
            if overrideSpoiler != OverrideSpoiler.NO_OVERRIDE:
                handler_response['spoiler'] = overrideSpoiler == OverrideSpoiler.SPOILER
            if removeDescription:
                handler_response['text'] = ""
            send_post_to_tg(message, handler_response)
        else:
            print("Can't handle instagram link: ")
            print(*link, sep="?")
            print("Falling back to InstaEmbedRouter")
            fallback = instagram_handler.handle_fallback(link[0])
            if fallback is not None:
                send_post_to_tg(message, fallback.to_legacy_dict())

    r = re.compile(booru_handler.URL_REGEX)
    booruLinks = list(filter(r.match, msgContent))
    for link in booruLinks:
        link = link.split("?")  # we don't need parameters after ?
        post_data = booru_handler.handle(link[0])
        if post_data is not None:
            handler_response = post_data.to_legacy_dict()
            if overrideSpoiler != OverrideSpoiler.NO_OVERRIDE:
                handler_response['spoiler'] = overrideSpoiler == OverrideSpoiler.SPOILER
            if removeDescription:
                handler_response['text'] = ""
            send_post_to_tg(message, handler_response)
        else:
            print("Can't handle *booru link: ")
            print(*link, sep="?")

    r = re.compile(demoty_handler.URL_REGEX)
    demotyLinks = list(filter(r.match, msgContent))
    for link in demotyLinks:
        link = link.split("?")  # we don't need parameters after ?
        post_data = demoty_handler.handle(link[0])
        if post_data is not None:
            handler_response = post_data.to_legacy_dict()
            if overrideSpoiler != OverrideSpoiler.NO_OVERRIDE:
                handler_response['spoiler'] = overrideSpoiler == OverrideSpoiler.SPOILER
            if removeDescription:
                handler_response['text'] = ""
            send_post_to_tg(message, handler_response)
        else:
            print("Can't handle demotywatory link: ")
            print(*link, sep="?")

    r = re.compile(tiktok_handler.URL_REGEX)
    ttLinks = list(filter(r.match, msgContent))
    for link in ttLinks:
        link = link.split("?")  # we don't need parameters after ?
        try:
            post_data = tiktok_handler.handle(link[0])
            if post_data is not None:
                handler_response = post_data.to_legacy_dict()
                if overrideSpoiler != OverrideSpoiler.NO_OVERRIDE:
                    handler_response['spoiler'] = overrideSpoiler == OverrideSpoiler.SPOILER
                if removeDescription:
                    handler_response['text'] = ""
                send_post_to_tg(message, handler_response)
            else:
                print("Can't handle tiktok link: ")
                print(*link, sep="?")
                print("Falling back to FxTikTok")
                fallback = tiktok_handler.handle_fallback(link[0])
                if fallback is not None:
                    send_post_to_tg(message, fallback.to_legacy_dict())
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            traceback.print_exception(type(e), e, e.__traceback__)
            print()
            print("Can't handle tiktok link: ")
            print(*link, sep="?")
            print("Falling back to FxTikTok")
            fallback = tiktok_handler.handle_fallback(link[0])
            if fallback is not None:
                send_post_to_tg(message, fallback.to_legacy_dict())

    if YOUTUBE_SUPPORT_ENABLED:
        r = re.compile(youtube_handler.URL_REGEX)
        ytLinks = list(filter(r.match, msgContent))
        for link in ytLinks:
            post_data = youtube_handler.handle(link)
            if post_data is not None:
                handler_response = post_data.to_legacy_dict()
                if removeDescription:
                    handler_response['text'] = ""
                send_post_to_tg(message, handler_response)
            else:
                print("Can't handle youtube link: " + str(link))


@bot.message_handler(regexp="^\s*(>>|»)(\!|\?)?\d+\s*", func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
def handle_derpibooru_magic_character_request(message):
    msg_text = message.text.strip()
    msg_text = msg_text.lstrip(">>").lstrip("»")

    if msg_text.startswith("!"):
        post_data = booru_handler.handle_with_options(
            "https://derpibooru.org/{}".format(msg_text.lstrip("!")), allow_nsfw=True, spoil_nsfw=False)
    elif msg_text.startswith("?"):
        post_data = booru_handler.handle_with_options(
            "https://derpibooru.org/{}".format(msg_text.lstrip("?")))
    else:
        post_data = booru_handler.handle_with_options(
            "https://derpibooru.org/{}".format(msg_text), allow_nsfw=False)

    if post_data is not None:
        send_post_to_tg(message, post_data.to_legacy_dict())
    else:
        print("Can't handle derpibooru img {}".format(msg_text))


def send_post_to_tg(orig_tg_msg, handler_response, msg_to_reply_to=None, caption_suffix=""):
    caption = prepare_caption(handler_response)
    if msg_to_reply_to is None:
        msg_to_reply_to = orig_tg_msg

    if caption_suffix:
        caption.long += caption_suffix

    match (handler_response['type']):
        case "media":
            return send_media_post(orig_tg_msg, handler_response, caption, msg_to_reply_to)
        case "text":
            return send_text_post(orig_tg_msg, caption, msg_to_reply_to)
        case _:
            return bot.reply_to(msg_to_reply_to, ERROR_MESSAGE)


def prepare_caption(handler_response):
    long_caption = ""
    short_caption = ""
    if "text" in handler_response:
        handler_response['text'] = remove_hashtags(handler_response['text'])
        long_caption += handler_response['text']
    if "author" in handler_response:
        long_caption += "\n\nby: " + handler_response['author']
        short_caption += "by: " + handler_response['author']
    if "url" in handler_response:
        long_caption += "\n" + handler_response['url']
        short_caption += "\n" + handler_response['url']
    long_caption = escape_markdown(long_caption)
    short_caption = escape_markdown(short_caption)

    if "poll" in handler_response and handler_response['poll'] == True:
        long_caption = "*This post is a poll\!*\n\n" + long_caption

    if handler_response['site'] == "twitter" and "community_note" in handler_response and handler_response['community_note'] == True:
        long_caption += parse_community_notes(handler_response)

    return Caption(short_caption, long_caption)


def remove_hashtags(text):
    # Remove hashtags when there are 4 or more grouped together
    # # and eveyrthing not being a whitespace is considered a signle hashtag
    text = re.sub(r'((#[^\s]+)\s+){3,}(#[^\s]+)', '', text, flags=re.UNICODE)
    # Removing hashtags may leave some empty lines so we need to remove them
    text = text.strip()
    return text


def parse_community_notes(handler_response):
    if "community_note_links" not in handler_response:
        return "\n\n*This tweet has community notes*:\n" + escape_markdown(handler_response['community_note_text'])

    note_arr = []
    split_indices = []
    links = []
    text = handler_response['community_note_text']

    split_indices.append(0)
    for link in handler_response['community_note_links']:
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


def prepare_twitter_send_context(orig_tg_msg, handler_response):
    msg_to_reply_to = orig_tg_msg
    caption_suffix = ""

    handle_reply, handle_quote = check_if_reply_quote_should_be_handled(
        orig_tg_msg, handler_response)

    if handler_response['quote']:
        if handle_quote:
            msg_to_reply_to, caption_suffix = resolve_and_send_related_twitter_post(
                orig_tg_msg,
                handler_response['quote_url'],
                msg_to_reply_to,
                caption_suffix,
                add_info_about_quote_to_caption,
            )
        else:
            caption_suffix = add_info_about_quote_to_caption(
                caption_suffix, handler_response['quote_url'])

    if handler_response['reply']:
        if handle_reply:
            msg_to_reply_to, caption_suffix = resolve_and_send_related_twitter_post(
                orig_tg_msg,
                handler_response['reply_url'],
                msg_to_reply_to,
                caption_suffix,
                add_info_about_reply_to_caption,
            )
        else:
            caption_suffix = add_info_about_reply_to_caption(
                caption_suffix, handler_response['reply_url'])

    return msg_to_reply_to, caption_suffix


def resolve_and_send_related_twitter_post(orig_tg_msg, related_url, msg_to_reply_to, caption_suffix, add_info_to_caption):
    post_data_for_related_tweet = twitter_handler.handle(related_url)
    if post_data_for_related_tweet is None:
        print("Can't handle twitter link: " + related_url)
        caption_suffix = add_info_to_caption(caption_suffix, related_url)
        return msg_to_reply_to, caption_suffix

    handler_response_for_related_tweet = post_data_for_related_tweet.to_legacy_dict()
    related_msg_to_reply_to, related_caption_suffix = prepare_twitter_send_context(
        orig_tg_msg, handler_response_for_related_tweet)
    msg_to_reply_to = send_post_to_tg(
        orig_tg_msg,
        handler_response_for_related_tweet,
        msg_to_reply_to=related_msg_to_reply_to,
        caption_suffix=related_caption_suffix,
    )

    return msg_to_reply_to, caption_suffix


def check_if_reply_quote_should_be_handled(orig_tg_msg, handler_response):
    if orig_tg_msg.chat.id in ALLOWED_CHATS:
        return False, False

    handle_reply, handle_quote = False, False

    if handler_response['quote']:
        handle_quote = True
    if handler_response['reply']:
        handle_quote = False
        handle_reply = True

    return handle_reply, handle_quote


def add_info_about_quote_to_caption(caption, quote_url):
    caption += "\n\n*Note:* This message is a quote tweet of: " + \
        escape_markdown(quote_url)
    return caption


def add_info_about_reply_to_caption(caption, reply_url):
    caption += "\n\n*Note:* This message is a reply to: " + \
        escape_markdown(reply_url)
    return caption


def send_media_post(orig_tg_msg, handler_response, caption, msg_to_reply_to):
    if len(handler_response['media']) == 1:
        return send_singular_media_post(
            orig_tg_msg, handler_response, caption, msg_to_reply_to)
    else:
        return send_multiple_media_post(
            orig_tg_msg, handler_response, caption, msg_to_reply_to)


def send_singular_media_post(orig_tg_msg, handler_response, caption, msg_to_reply_to):
    media = handler_response['media'][0]
    if media[1] == "photo":
        sent_message = send_photo_post(
            orig_tg_msg, media[0], caption, handler_response['spoiler'], msg_to_reply_to)
    elif media[1] == "video":
        sent_message = send_video_post(
            orig_tg_msg, media[0], caption, handler_response['spoiler'], msg_to_reply_to)
    elif media[1] == "video_file":
        video_file = open(media[0], "rb")
        sent_message = send_video_post(
            orig_tg_msg, video_file, caption, handler_response['spoiler'], msg_to_reply_to)
    elif media[1] == "gif":
        sent_message = send_gif_post(
            orig_tg_msg, media[0], caption, handler_response['spoiler'], msg_to_reply_to)
    else:
        print("This type of media (" + media[1] + ") is not supported.")
        print(handler_response)
        return orig_tg_msg

    delete_handled_message(orig_tg_msg)
    return sent_message


def send_photo_post(orig_tg_msg, photo, caption, has_spoiler, msg_to_reply_to):
    if len(caption.long) <= 1024:
        sent_message = bot.send_photo(chat_id=orig_tg_msg.chat.id,
                                      photo=photo,
                                      caption=caption.long,
                                      has_spoiler=has_spoiler,
                                      reply_parameters=ReplyParameters(
                                          message_id=msg_to_reply_to.message_id,
                                          allow_sending_without_reply=True))
    else:
        # TODO: secure for over 4096 characters
        sent_message = bot.send_photo(chat_id=orig_tg_msg.chat.id,
                                      photo=photo,
                                      caption=caption.short,
                                      has_spoiler=has_spoiler,
                                      reply_parameters=ReplyParameters(
                                          message_id=msg_to_reply_to.message_id,
                                          allow_sending_without_reply=True))
        sent_message = bot.send_message(chat_id=orig_tg_msg.chat.id,
                                        text=caption.long,
                                        reply_parameters=ReplyParameters(
                                            message_id=sent_message.message_id),
                                        link_preview_options=LinkPreviewOptions(is_disabled=True))
    return sent_message


def send_video_post(orig_tg_msg, video, caption, has_spoiler, msg_to_reply_to):
    if len(caption.long) <= 1024:
        sent_message = bot.send_video(chat_id=orig_tg_msg.chat.id,
                                      video=video,
                                      caption=caption.long,
                                      has_spoiler=has_spoiler,
                                      reply_parameters=ReplyParameters(
                                          message_id=msg_to_reply_to.message_id,
                                          allow_sending_without_reply=True))
    else:
        # TODO: secure for over 4096 characters
        sent_message = bot.send_video(chat_id=orig_tg_msg.chat.id,
                                      video=video,
                                      caption=caption.short,
                                      has_spoiler=has_spoiler,
                                      reply_parameters=ReplyParameters(
                                          message_id=msg_to_reply_to.message_id,
                                          allow_sending_without_reply=True))
        sent_message = bot.send_message(chat_id=orig_tg_msg.chat.id,
                                        text=caption.long,
                                        reply_parameters=ReplyParameters(
                                            message_id=sent_message.message_id),
                                        link_preview_options=LinkPreviewOptions(is_disabled=True))
    return sent_message


def send_gif_post(orig_tg_msg, gif, caption, has_spoiler, msg_to_reply_to):
    if len(caption.long) <= 1024:
        sent_message = bot.send_animation(chat_id=orig_tg_msg.chat.id,
                                          animation=gif,
                                          caption=caption.long,
                                          has_spoiler=has_spoiler,
                                          reply_parameters=ReplyParameters(
                                              message_id=msg_to_reply_to.message_id,
                                              allow_sending_without_reply=True))
    else:
        # TODO: secure for over 4096 characters
        sent_message = bot.send_animation(chat_id=orig_tg_msg.chat.id,
                                          animation=gif,
                                          caption=caption.short,
                                          has_spoiler=has_spoiler,
                                          reply_parameters=ReplyParameters(
                                              message_id=msg_to_reply_to.message_id,
                                              allow_sending_without_reply=True))
        sent_message = bot.send_message(chat_id=orig_tg_msg.chat.id,
                                        text=caption.long,
                                        reply_parameters=ReplyParameters(
                                            message_id=sent_message.message_id),
                                        link_preview_options=LinkPreviewOptions(is_disabled=True))
    return sent_message


def send_multiple_media_post(orig_tg_msg, handler_response, caption, msg_to_reply_to):
    media_group = []
    i = 0
    for media in handler_response['media']:
        if media[1] == "photo":
            media_group.append(InputMediaPhoto(
                media=media[0], has_spoiler=handler_response['spoiler']))
        elif media[1] == "video":
            media_group.append(InputMediaVideo(
                media=media[0], has_spoiler=handler_response['spoiler']))
        elif media[1] == "video_file":
            media_group.append(InputMediaVideo(
                media=open(media[0], "rb"), has_spoiler=handler_response['spoiler']))
        elif media[1] == "gif":
            filename = file_downloader.download_video(
                media[0], handler_response['site'], handler_response['id'] + "_" + str(i))
            i += 1
            media_group.append(InputMediaVideo(
                media=open(filename, "rb"), has_spoiler=handler_response['spoiler']))
        else:
            print("This type of media (" + media[1] + ") is not supported.")
            print(handler_response)

    if len(media_group) > 10:
        # media post in tg can have at most 10 media
        send_split_multiple_media_post(
            orig_tg_msg, media_group, caption, msg_to_reply_to)
    elif len(media_group) > 0:
        if len(caption.long) <= 1024:
            media_group[0].caption = caption.long
            # workaround for a bug in telebot, will be fixed in a newer than 4.17.0 release
            media_group[0].parse_mode = PARSE_MODE
            sent_message_arr = bot.send_media_group(chat_id=orig_tg_msg.chat.id,
                                                    media=media_group,
                                                    reply_parameters=ReplyParameters(
                                                        message_id=msg_to_reply_to.message_id,
                                                        allow_sending_without_reply=True))

            delete_handled_message(orig_tg_msg)
            # send_media_group returns an array of msgs, we need just the first one
            return sent_message_arr[0]
        else:
            # TODO: secure for over 4096 characters
            media_group[0].caption = caption.short
            sent_message_arr = bot.send_media_group(chat_id=orig_tg_msg.chat.id,
                                                    media=media_group,
                                                    reply_parameters=ReplyParameters(
                                                        message_id=msg_to_reply_to.message_id,
                                                        allow_sending_without_reply=True))
            sent_message_with_caption = bot.send_message(chat_id=orig_tg_msg.chat.id,
                                                         text=caption.long,
                                                         reply_parameters=ReplyParameters(
                                                             message_id=sent_message_arr[0].message_id),
                                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
            delete_handled_message(orig_tg_msg)
            return sent_message_with_caption
    else:
        print("Multi media post doesn't contain any supported media.")
        print(handler_response)
        return orig_tg_msg


def send_split_multiple_media_post(orig_tg_msg, media_group, caption, msg_to_reply_to):
    # split media_group into chunks of 10 elements
    chunk_size = 10
    media_groups = [media_group[i:i + chunk_size]
                    for i in range(0, len(media_group), 10)]
    for i in range(len(media_groups)):
        media_groups[i][0].caption = caption.short
        # workaround for a bug in telebot, will be fixed in a newer than 4.17.0 release
        media_groups[i][0].parse_mode = PARSE_MODE
        sent_message_arr = bot.send_media_group(chat_id=orig_tg_msg.chat.id,
                                                media=media_groups[i],
                                                reply_parameters=ReplyParameters(
                                                    message_id=msg_to_reply_to.message_id,
                                                    allow_sending_without_reply=True))
        # next msg shall reply to the previous one
        msg_to_reply_to = sent_message_arr[0]

    sent_message_with_caption = bot.send_message(chat_id=orig_tg_msg.chat.id,
                                                 text=caption.long,
                                                 reply_parameters=ReplyParameters(
                                                     message_id=msg_to_reply_to.message_id),
                                                 link_preview_options=LinkPreviewOptions(is_disabled=True))

    delete_handled_message(orig_tg_msg)
    return sent_message_with_caption


def send_text_post(orig_tg_msg, caption, msg_to_reply_to):
    sent_message = bot.send_message(chat_id=orig_tg_msg.chat.id,
                                    text=caption.long,
                                    reply_parameters=ReplyParameters(
                                        message_id=msg_to_reply_to.message_id,
                                        allow_sending_without_reply=True),
                                    link_preview_options=LinkPreviewOptions(is_disabled=True))
    delete_handled_message(orig_tg_msg)
    return sent_message


@bot.message_handler(regexp="http", func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
def handle_link(message):
    if message.chat.id not in ALLOWED_CHATS:
        bot.reply_to(message, "This site is not supported yet\.")


@bot.message_handler(regexp="test", func=lambda message: message.from_user.id in ALLOWED_USERS)
def test(message):
    pass


def delete_handled_message(message):
    try:
        bot.delete_message(message.chat.id, message.id)
    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        print(str(e))
        print("Cant remove message in chat " +
              str(message.chat.title) + " (" + str(message.chat.id) + ").")
        print()


def signal_handler(signum, frame):
    print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
    print("Captured signal: " + str(signum))
    print("Traceback (most recent call last):")
    traceback.print_stack(frame)
    print()
    if signum == signal.SIGINT or signum == signal.SIGTERM:
        sys.exit(signum)

# def main():


for sig in set(signal.Signals):
    try:
        signal.signal(sig, signal_handler)
        print("Handler for signal " + str(sig) + " set.")
    except (ValueError, OSError, RuntimeError) as _:
        pass

while True:
    try:
        bot.polling()
    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print()
