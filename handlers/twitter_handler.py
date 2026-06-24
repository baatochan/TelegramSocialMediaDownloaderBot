import json
import time
import traceback

import requests


def handle_url(link):
    headers = {'User-Agent': "Telegram Social Media Downloader Bot"}
    link_parts = link.split('/')
    status_id = link_parts.index('status')
    id = link_parts[status_id + 1]
    try:
        response = requests.get(
            "https://api.fxtwitter.com/tgSocialMediaDownloaderBot/status/" + id, headers=headers)
        result = json.loads(response.text)
        if result['code'] == 200:
            return handle_tweet(result['tweet'])
        else:
            return {}
    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print("Couldn't get tweet from url: " + link)
        print()
        return {}


def handle_tweet(tweet):
    return_data = {}
    return_data['site'] = "twitter"
    return_data['id'] = tweet['id']

    return_data['text'] = tweet['text']
    return_data['author'] = tweet['author']['name'] + \
        " (@" + tweet['author']['screen_name'] + ")"
    return_data['url'] = tweet['url']

    if "media" in tweet and tweet['media'] is not None:
        if "all" in tweet['media'] and tweet['media']['all'] is not None:
            return_data['type'] = "media"
            return_data['media'] = []
            for media in tweet['media']['all']:
                return_data['media'].append([media['url'], media['type']])
            if "possibly_sensitive" in tweet and tweet['possibly_sensitive'] is not None:
                return_data['spoiler'] = tweet['possibly_sensitive']
            else:
                return_data['spoiler'] = False
        else:
            return_data['type'] = "text"
            # When media is present but media.all is not, then there has to be
            # media.external which is an embed for external media such as yt
            # video. The link to that video is already added to the post text
            # by the API so I don't have to do anything with it.
    else:
        return_data['type'] = "text"

    return_data = get_reply_quote_status(return_data, tweet)

    return_data = check_if_poll(return_data, tweet)
    if "community_note" in tweet and tweet['community_note'] is not None:
        return_data = check_community_notes(return_data, tweet)

    return return_data


def get_reply_quote_status(return_data, tweet):
    if "quote" in tweet and tweet['quote'] is not None:
        return_data['quote'] = True
        return_data['quote_url'] = tweet['quote']['url']
    else:
        return_data['quote'] = False

    if "replying_to" in tweet and tweet['replying_to'] is not None:
        if "replying_to_status" in tweet and tweet['replying_to_status'] is not None:
            return_data['reply'] = True
            return_data['reply_url'] = "https://twitter.com/" + \
                tweet['replying_to'] + "/status/" + tweet['replying_to_status']
        else:
            return_data['reply'] = False
    else:
        return_data['reply'] = False

    return return_data


def check_if_poll(return_data, tweet):
    if "poll" in tweet and tweet['poll'] is not None:
        return_data['poll'] = True
        for choice in tweet['poll']['choices']:
            return_data['text'] += "\n * " + choice['label'] + \
                " (" + str(choice['percentage']) + "%)"
    else:
        return_data['poll'] = False
    return return_data


def check_community_notes(return_data, tweet):
    return_data['community_note'] = True
    return_data['community_note_text'] = tweet['community_note']['text']
    if "entities" in tweet['community_note']:
        return_data['community_note_links'] = []
        for entity in tweet['community_note']['entities']:
            return_data['community_note_links'].append({"from": entity['fromIndex'],
                                                        "to": entity['toIndex'],
                                                        "url": entity['ref']['url']})
    return return_data
