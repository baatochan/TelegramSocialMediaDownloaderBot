#!/usr/bin/env python3
import configparser
import json
import os
import signal
import sys
import time
import traceback
from types import FrameType

import telebot
from telebot.formatting import escape_markdown
from tendo import singleton

from handlers import (
    BooruHandler,
    HandlerRegistry,
)
from post_orchestrator import PostOrchestrator
from post_data_sender import PostDataSender
from related_post_resolver import RelatedPostResolver
from telegram_routes import register_handlers, register_special_derpibooru_handler


me = singleton.SingleInstance()  # will sys.exit(-1) if other instance is running


def load_config_or_exit(config_path: str = "config.txt") -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if os.path.isfile(config_path):
        config.read(config_path)
        return config

    print("No config file. Create config file and run the script again.")
    sys.exit(1)


def signal_handler(signum: int, frame: FrameType | None) -> None:
    print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
    print("Captured signal: " + str(signum))
    print("Traceback (most recent call last):")
    traceback.print_stack(frame)
    print()
    sys.exit(signum)


def register_shutdown_signal_handlers() -> None:
    shutdown_signals = [signal.SIGINT, signal.SIGTERM]

    for signal_name in ("SIGHUP", "SIGQUIT"):
        shutdown_signal = getattr(signal, signal_name, None)
        if shutdown_signal is not None:
            shutdown_signals.append(shutdown_signal)

    for sig in shutdown_signals:
        signal.signal(sig, signal_handler)
        print("Handler for signal " + str(sig) + " set.")


def run_polling_forever(bot: telebot.TeleBot) -> None:
    while True:
        try:
            bot.polling()
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            traceback.print_exception(type(e), e, e.__traceback__)
            print()


def main() -> None:
    config = load_config_or_exit()
    allowed_users = json.loads(config['config']['allowed_users'])
    allowed_chats = json.loads(config['config']['allowed_chats'])

    bot = telebot.TeleBot(config['config']['token'])
    bot.parse_mode = "MarkdownV2"
    bot_id = bot.get_me().id

    error_message = escape_markdown(
        "Can't download this post. Try again later.")
    post_data_sender = PostDataSender(bot, error_message)
    related_post_resolver = RelatedPostResolver()
    post_orchestrator = PostOrchestrator(
        post_data_sender,
        related_post_resolver,
        allowed_chats,
    )

    handler_registry = HandlerRegistry.create_from_config(config)
    handlers_to_process = handler_registry.get_active_handlers()
    supported_sites_regex = handler_registry.get_active_combined_regex()

    # Site-specific workflows still need direct access to selected handlers.
    booru_handler = handler_registry.get_handler(BooruHandler.SITE_NAME)

    register_handlers(
        bot,
        config,
        allowed_users,
        allowed_chats,
        bot_id,
        handlers_to_process,
        supported_sites_regex,
        post_orchestrator,
    )

    register_special_derpibooru_handler(
        bot,
        allowed_users,
        allowed_chats,
        booru_handler,
        post_data_sender,
    )

    register_shutdown_signal_handlers()
    run_polling_forever(bot)


if __name__ == "__main__":
    main()
