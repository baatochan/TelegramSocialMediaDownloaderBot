import json

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
        # Handle the exception here
        print("An error occurred:", str(e))


def handle_tweet(tweet):
    return_data = {}
    return_data['site'] = "twitter"
    return_data['id'] = tweet["id"]

    return_data = get_reply_quote_status(return_data, tweet)

    if "media" in tweet:
        return_data['type'] = "media"
        return_data['media'] = []
        for media in tweet["media"]["all"]:
            return_data['media'].append([media["url"], media["type"]])
        return_data['spoiler'] = tweet['possibly_sensitive']
    else:
        return_data['type'] = "text"

    return_data['text'] = tweet["text"]
    return_data['author'] = tweet["author"]["name"] + \
        " (@" + tweet["author"]["screen_name"] + ")"
    return_data['url'] = tweet['url']

    return_data = check_if_poll(return_data, tweet)

    return return_data


def get_reply_quote_status(return_data, tweet):
    if "quote" in tweet:
        return_data["quote"] = True
        return_data["quote_url"] = tweet["quote"]["url"]
    else:
        return_data["quote"] = False

    if tweet["replying_to"] != None:
        return_data["reply"] = True
        return_data["reply_url"] = "https://twitter.com/" + \
            tweet["replying_to"] + "/status/" + tweet["replying_to_status"]
    else:
        return_data["reply"] = False

    return return_data


def check_if_poll(return_data, tweet):
    if "poll" in tweet:
        return_data['poll'] = True
        for choice in tweet['poll']['choices']:
            return_data['text'] += "\n * " + choice['label'] + \
                " (" + str(choice['percentage']) + "%)"
    else:
        return_data['poll'] = False
    return return_data
