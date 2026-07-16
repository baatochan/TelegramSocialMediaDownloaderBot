#!/usr/bin/env python3
import configparser
import json
import os
import re
import signal
import sys
import time
import traceback

import telebot
from telebot.formatting import escape_markdown
from tendo import singleton

from handlers import (
    BooruHandler,
    HandlerRegistry,
)
from post_handling_policies import DescriptionPolicy, PostHandlingPolicies, SpoilerPolicy
from post_orchestrator import PostOrchestrator
from post_data_sender import PostDataSender
from related_post_resolver import RelatedPostResolver


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
related_post_resolver = RelatedPostResolver()
post_orchestrator = PostOrchestrator(
    post_data_sender,
    related_post_resolver,
    ALLOWED_CHATS,
)

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

    post_handling_policies = parse_post_handling_policies(message.text)

    msgContent = message.text.split()

    for handler in handlers_to_process:
        links = extract_site_links(msgContent, handler.URL_REGEX)
        for link in links:
            post_orchestrator.process_site_link(
                message,
                link,
                handler,
                post_handling_policies=post_handling_policies,
            )


def parse_post_handling_policies(message_text: str) -> PostHandlingPolicies:
    if "BBspoiler=True" in message_text:
        spoiler_policy = SpoilerPolicy.FORCE_SPOILER
    elif "BBspoiler=False" in message_text:
        spoiler_policy = SpoilerPolicy.FORCE_NO_SPOILER
    else:
        spoiler_policy = SpoilerPolicy.KEEP_ORIGINAL

    if "BBnoDesc=True" in message_text:
        description_policy = DescriptionPolicy.REMOVE_DESCRIPTION
    else:
        description_policy = DescriptionPolicy.KEEP_ORIGINAL

    return PostHandlingPolicies(
        spoiler_policy=spoiler_policy,
        description_policy=description_policy,
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
