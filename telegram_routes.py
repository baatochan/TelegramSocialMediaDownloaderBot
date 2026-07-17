import configparser
import re
from collections.abc import Collection

import telebot
from telebot.formatting import escape_markdown
from telebot.types import Message

from post_data_sender import PostDataSender
from post_handling_policies import DescriptionPolicy, PostHandlingPolicies, SpoilerPolicy
from post_orchestrator import PostOrchestrator


def register_handlers(
    bot: telebot.TeleBot,
    config: configparser.ConfigParser,
    allowed_users: Collection[int],
    allowed_chats: Collection[int],
    bot_id: int,
    handlers_to_process,
    supported_sites_regex: str,
    post_orchestrator: PostOrchestrator,
) -> None:
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message: Message) -> None:
        if message.from_user.id in allowed_users:
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

    @bot.message_handler(regexp=supported_sites_regex, func=lambda message: message.from_user.id in allowed_users or message.chat.id in allowed_chats)
    def handle_supported_site(message: Message) -> None:
        if message.forward_origin and message.forward_origin.type == "user" and message.forward_origin.sender_user.id == bot_id:
            return

        post_handling_policies = parse_post_handling_policies(message.text)

        msg_content = message.text.split()

        for handler in handlers_to_process:
            links = extract_site_links(msg_content, handler.URL_REGEX)
            for link in links:
                post_orchestrator.process_link_for_handler(
                    message,
                    link,
                    handler,
                    post_handling_policies=post_handling_policies,
                )

    @bot.message_handler(regexp="http", func=lambda message: message.from_user.id in allowed_users or message.chat.id in allowed_chats)
    def handle_link(message: Message) -> None:
        if message.chat.id not in allowed_chats:
            bot.reply_to(message, "This site is not supported yet\.")

    @bot.message_handler(regexp="test", func=lambda message: message.from_user.id in allowed_users)
    def test(message: Message) -> None:
        pass


def register_special_derpibooru_handler(
    bot: telebot.TeleBot,
    allowed_users: Collection[int],
    allowed_chats: Collection[int],
    booru_handler,
    post_data_sender: PostDataSender,
) -> None:
    @bot.message_handler(regexp="^\s*(>>|»)(\!|\?)?\d+\s*", func=lambda message: message.from_user.id in allowed_users or message.chat.id in allowed_chats)
    def handle_derpibooru_magic_character_request(message: Message) -> None:
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
