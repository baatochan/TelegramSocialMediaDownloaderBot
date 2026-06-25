import json
import time
import traceback

import requests

from handlers.base import MediaHandler, PostData


class TwitterHandler(MediaHandler):
    def handle(self, link: str) -> PostData | None:
        headers = {'User-Agent': "Telegram Social Media Downloader Bot"}
        link_parts = link.split('/')
        status_id = link_parts.index('status')
        post_id = link_parts[status_id + 1]

        try:
            response = requests.get(
                "https://api.fxtwitter.com/tgSocialMediaDownloaderBot/status/" + post_id,
                headers=headers,
            )
            result = json.loads(response.text)

            if result.get('code') != 200:
                return None

            return self._handle_tweet(result['tweet'])
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            traceback.print_exception(type(e), e, e.__traceback__)
            print("Couldn't get tweet from url: " + link)
            print()
            return None

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

        if "media" in tweet and tweet['media'] is not None:
            if "all" in tweet['media'] and tweet['media']['all'] is not None:
                post_data.post_type = "media"
                for media in tweet['media']['all']:
                    post_data.media.append([media['url'], media['type']])
                if "possibly_sensitive" in tweet and tweet['possibly_sensitive'] is not None:
                    post_data.spoiler = tweet['possibly_sensitive']
            else:
                post_data.post_type = "text"
                # When media is present but media.all is not, then there has to be
                # media.external which is an embed for external media such as yt.
                # The link to that video is already added to the post text by API.

        self._get_reply_quote_status(post_data, tweet)
        self._check_if_poll(post_data, tweet)
        self._check_community_notes(post_data, tweet)

        return post_data

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
