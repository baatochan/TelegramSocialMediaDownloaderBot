import json
import time
import traceback

import requests


def handle_url(link):
    headers = {'User-Agent': "Telegram Social Media Downloader Bot"}
    try:
        response = requests.post(
            "https://tikwm.com/api", params={'url': str(link)}, headers=headers)
        result = json.loads(response.text)
        if result['code'] == 0:
            return handle_tiktok(result['data'], link)
        else:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            print("Couldn't get tiktok from url: " + link)
            print(json.dumps(result, indent=2))
            print()
            return {}
    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        print("Couldn't get tiktok from url: " + link)
        traceback.print_exception(type(e), e, e.__traceback__)
        print()
        return {}


def handle_tiktok(post, original_url):
    return_data = {}
    return_data['site'] = "tiktok"
    return_data['id'] = post['id']
    return_data['url'] = original_url
    return_data['spoiler'] = False

    if 'title' in post and post['title'] is not None:
        return_data['text'] = post['title']

    if 'author' in post and post['author'] is not None:
        return_data['author'] = "@" + post['author']['unique_id']

    # Handle an image post
    if 'images' in post and post['images'] is not None:
        return_data['type'] = "media"
        # Check if the post has a video and images
        return_data['media'] = check_if_video_present(post)
        for image in post['images']:
            return_data['media'].append([image, "photo"])
        # Add a note about a bg music
        if 'music' in post and post['music'] is not None:
            music_url = post['music']
            # we don't need parameters after ?
            music_url = music_url.split("?")
            music_note = "Link to the background audio: " + music_url[0]
            if 'text' in return_data:
                return_data['text'] += "\n\n" + music_note
            else:
                return_data['text'] = music_note
    # Handle a video post
    else:
        # vmplay is hd video, play is sd video
        if 'vmplay' in post and post['vmplay'] is not None:
            return_data['type'] = "media"
            video_url = post['vmplay']
            # we don't need parameters after ?
            video_url = video_url.split("?")
            return_data['media'] = [[video_url[0], "video"]]
        elif 'play' in post and post['play'] is not None:
            return_data['type'] = "media"
            video_url = post['play']
            # we don't need parameters after ?
            video_url = video_url.split("?")
            return_data['media'] = [[video_url[0], "video"]]

    return return_data


def check_if_video_present(post):
    return_media = []
    if 'vmplay' in post and post['vmplay'] is not None and 'music' in post and post['music'] is not None:
        if post['vmplay'] != post['music']:
            video_url = post['vmplay']
            # we don't need parameters after ?
            video_url = video_url.split("?")
            return_media.append([video_url[0], "video"])
    elif 'play' in post and post['play'] is not None and 'music' in post and post['music'] is not None:
        if post['play'] != post['music']:
            video_url = post['play']
            # we don't need parameters after ?
            video_url = video_url.split("?")
            return_media.append([video_url[0], "video"])

    return return_media
