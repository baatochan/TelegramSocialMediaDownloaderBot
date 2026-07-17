import json
import time
import traceback

import requests

from handlers.base import MediaHandler, PostData


class TwitterHandler(MediaHandler):
    SITE_NAME = "twitter"
    URL_REGEX = r"((http(s)?://)|^| )(www\.)?((fixup|fixv)?x|(fx|vx)?twitter)\.com/.+"

    def handle(self, link: str) -> PostData | None:
        link_parts = link.split('/')
        status_id = link_parts.index('status')
        post_id = link_parts[status_id + 1]

        try:
            tweet = self._fetch_tweet(post_id)
            if tweet is None:
                return None

            tweet_lang = tweet.get("lang")
            if tweet_lang is not None and tweet_lang.lower() not in {"en", "pl"}:
                translated_tweet = self._fetch_tweet(
                    post_id, target_lang_code="en")
                if translated_tweet is not None:
                    return self._handle_tweet(translated_tweet)

            return self._handle_tweet(tweet)
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            traceback.print_exception(type(e), e, e.__traceback__)
            print("Couldn't get tweet from url: " + link)
            print()
            return None

    def _fetch_tweet(self, post_id: str, target_lang_code: str | None = None):
        headers = {'User-Agent': "Telegram Social Media Downloader Bot"}
        api_url = "https://api.fxtwitter.com/tgSocialMediaDownloaderBot/status/" + post_id
        # FxTwitter API expects a 2-letter ISO language code (for example: en, pl).
        if target_lang_code is not None:
            api_url += "/" + target_lang_code

        response = requests.get(api_url, headers=headers)
        result = json.loads(response.text)
        if result.get('code') != 200:
            return None

        return result['tweet']

    def _handle_tweet(self, tweet) -> PostData:
        post_data = PostData(
            site="twitter",
            post_type="text",
            post_id=tweet['id'],
            text=tweet['text'],
            author=tweet['author']['name'] +
            " (@" + tweet['author']['screen_name'] + ")",
            url=tweet['url'],
        )

        self._check_media(post_data, tweet)

        self._use_translation_if_present(post_data, tweet)
        self._get_reply_quote_status(post_data, tweet)
        self._check_if_poll(post_data, tweet)
        self._check_community_notes(post_data, tweet)

        return post_data

    def _check_media(self, post_data, tweet):
        media = tweet.get("media")
        if media is None:
            return

        all_media = media.get("all")
        if all_media is None:
            # When media is present but media.all is not, then there has to be
            # media.external which is an embed for external media such as yt.
            # The link to that video is already added to the post text by API.
            post_data.post_type = "text"
            return

        post_data.post_type = "media"
        for media_item in all_media:
            post_data.media.append([media_item['url'], media_item['type']])

        possibly_sensitive = tweet.get("possibly_sensitive")
        if possibly_sensitive is not None:
            post_data.spoiler = possibly_sensitive

    def _use_translation_if_present(self, post_data, tweet):
        translation = tweet.get("translation")
        if translation is None:
            return

        translated_text = translation.get("text")
        if translated_text is None:
            return

        post_data.text = translated_text

    def _get_reply_quote_status(self, post_data, tweet):
        quote = tweet.get("quote")
        post_data.quote = quote is not None
        if quote is not None:
            post_data.quote_url = quote['url']

        replying_to = tweet.get("replying_to")
        replying_to_status = tweet.get("replying_to_status")
        post_data.reply = replying_to is not None and replying_to_status is not None
        if post_data.reply:
            post_data.reply_url = "https://twitter.com/" + \
                replying_to + "/status/" + replying_to_status

    def _check_if_poll(self, post_data, tweet):
        poll = tweet.get("poll")
        if poll is None:
            post_data.poll = False
            return

        post_data.poll = True
        for choice in poll['choices']:
            post_data.text += "\n * " + \
                choice['label'] + " (" + str(choice['percentage']) + "%)"

    def _check_community_notes(self, post_data, tweet):
        community_note = tweet.get("community_note")
        if community_note is None:
            post_data.community_note = False
            return

        post_data.community_note = True
        post_data.community_note_text = community_note['text']

        entities = community_note.get("entities")
        if entities is None:
            return

        for entity in entities:
            post_data.community_note_links.append(
                {
                    "from": entity['fromIndex'],
                    "to": entity['toIndex'],
                    "url": entity['ref']['url'],
                }
            )
