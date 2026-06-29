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
from tendo import singleton

from handlers import (
    BooruHandler,
    HandlerRegistry,
)
from post_data_sender import PostDataSender
from related_post_resolver import RelatedPostResolver


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

bot = telebot.TeleBot(config['config']['token'])
BOT_ID = bot.get_me().id
PARSE_MODE = "MarkdownV2"
bot.parse_mode = PARSE_MODE

ERROR_MESSAGE = escape_markdown("Can't download this post. Try again later.")

post_data_sender = PostDataSender(bot, ERROR_MESSAGE)
related_post_resolver = RelatedPostResolver(post_data_sender)

handler_registry = HandlerRegistry.create_from_config(config)
handlers_to_process = handler_registry.get_active_handlers()
supported_sites_regex = handler_registry.get_active_combined_regex()

# Site-specific workflows still need direct access to selected handlers.
booru_handler = handler_registry.get_handler(BooruHandler.SITE_NAME)


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


@bot.message_handler(regexp=supported_sites_regex, func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
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

    for handler in handlers_to_process:
        links = extract_site_links(msgContent, handler.URL_REGEX)
        for link in links:
            process_site_link(
                message,
                link,
                handler,
                overrideSpoiler,
                removeDescription,
            )


def normalize_message_token(token: str) -> str:
    token = token.strip()
    token = token.lstrip("'\"([{<")
    token = token.rstrip(".,!?;:'\"])}>")
    return token


def extract_site_links(msg_content: list[str], url_regex: str) -> list[str]:
    r = re.compile(url_regex)
    links = []
    for token in msg_content:
        normalized_token = normalize_message_token(token)
        if not normalized_token:
            continue

        if r.match(normalized_token.lower()):
            links.append(normalized_token)

    return links


def process_site_link(message, link: str, handler, override_spoiler,
                      remove_description: bool) -> None:
    site_label = handler.SITE_NAME
    link_to_handle = handler.normalize_url(link)

    post_data = handler.handle(link_to_handle)
    if post_data is None:
        print("Can't handle " + site_label + " link: " + str(link))

        post_data = handler.handle_fallback(link_to_handle)
        if post_data is None:
            return

    if override_spoiler != OverrideSpoiler.NO_OVERRIDE:
        post_data.spoiler = override_spoiler == OverrideSpoiler.SPOILER
    if remove_description:
        post_data.text = ""

    send_post_with_fallback(
        message,
        post_data,
        handler,
        link_to_handle,
    )


def send_post_with_fallback(message, post_data, handler, link_to_handle) -> None:
    try:
        if post_data.reply or post_data.quote:
            msg_to_reply_to, caption_suffix = related_post_resolver.prepare_send_context(
                message,
                post_data,
                handler,
                skip_resolution=message.chat.id in ALLOWED_CHATS,
            )
            post_data_sender.send(
                message,
                post_data,
                msg_to_reply_to=msg_to_reply_to,
                caption_suffix=caption_suffix,
            )
        else:
            post_data_sender.send(message, post_data)
    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print()
        print("Couldn't send " + handler.SITE_NAME +
              " post, trying fallback: " + str(link_to_handle))

        fallback_post_data = handler.handle_fallback(link_to_handle)
        if fallback_post_data is None:
            return

        post_data_sender.send(message, fallback_post_data)


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
        post_data_sender.send(message, post_data)
    else:
        print("Can't handle derpibooru img {}".format(msg_text))


@bot.message_handler(regexp="http", func=lambda message: message.from_user.id in ALLOWED_USERS or message.chat.id in ALLOWED_CHATS)
def handle_link(message):
    if message.chat.id not in ALLOWED_CHATS:
        bot.reply_to(message, "This site is not supported yet\.")


@bot.message_handler(regexp="test", func=lambda message: message.from_user.id in ALLOWED_USERS)
def test(message):
    pass


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
