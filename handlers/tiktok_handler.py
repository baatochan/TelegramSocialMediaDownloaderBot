import json
import time
import traceback

import requests
from handlers.base import MediaHandler, PostData


class TikTokHandler(MediaHandler):
    def handle(self, link: str) -> PostData | None:
        headers = {'User-Agent': "Telegram Social Media Downloader Bot"}
        try:
            response = requests.post(
                "https://tikwm.com/api", params={'url': str(link)}, headers=headers)
            result = json.loads(response.text)
            if result['code'] == 0:
                return self._handle_tiktok(result['data'], link)

            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            print("Couldn't get tiktok from url: " + link)
            print(json.dumps(result, indent=2))
            print()
            return None
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            print("Couldn't get tiktok from url: " + link)
            traceback.print_exception(type(e), e, e.__traceback__)
            print()
            return None

    def _handle_tiktok(self, post, original_url) -> PostData | None:
        post_data = PostData(
            site="tiktok",
            post_type="media",
            post_id=post['id'],
            url=original_url,
            spoiler=False,
        )

        if 'title' in post and post['title'] is not None:
            post_data.text = post['title']

        if 'author' in post and post['author'] is not None:
            post_data.author = "@" + post['author']['unique_id']

        # Handle an image post
        if 'images' in post and post['images'] is not None:
            # Check if the post has a video and images
            post_data.media = self._check_if_video_present(post)
            for image in post['images']:
                post_data.media.append([image, "photo"])

            # Add a note about a bg music
            if 'music' in post and post['music'] is not None:
                music_url = post['music']
                # we don't need parameters after ?
                music_url = music_url.split("?")
                music_note = "Link to the background audio: " + music_url[0]
                if post_data.text:
                    post_data.text += "\n\n" + music_note
                else:
                    post_data.text = music_note

            return post_data if post_data.media else None

        # Handle a video post
        # vmplay is hd video, play is sd video
        if 'vmplay' in post and post['vmplay'] is not None:
            video_url = post['vmplay']
            # we don't need parameters after ?
            video_url = video_url.split("?")
            post_data.media = [[video_url[0], "video"]]
            return post_data

        if 'play' in post and post['play'] is not None:
            video_url = post['play']
            # we don't need parameters after ?
            video_url = video_url.split("?")
            post_data.media = [[video_url[0], "video"]]
            return post_data

        return None

    def _check_if_video_present(self, post):
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
