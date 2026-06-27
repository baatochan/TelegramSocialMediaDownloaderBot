import json
import time
import traceback

import requests

import file_converter
import file_downloader
from handlers.base import MediaHandler, PostData


class BooruHandler(MediaHandler):
    URL_REGEX = r"((http(s)?://)|^| )(www\.)?[a-zA-Z]*booru\.org/.+"

    CONVERT_WEBM_VIDEO = False

    def handle(self, link: str) -> PostData | None:
        return self.handle_with_options(link)

    def handle_with_options(self, link: str, allow_nsfw: bool = True, spoil_nsfw: bool = True) -> PostData | None:
        headers = {'User-Agent': "Telegram Social Media Downloader Bot"}

        link_parts = link.split('/')

        # look for full site name, returns list of indexes
        site_idx = [i for i, item in enumerate(
            link_parts) if item.endswith('booru.org')]
        # the first index should point to the site name
        site_id = site_idx[0] if site_idx else None
        if not site_id:
            print("Couldn't get image from url (can't find the domain): " + link)
            print()
            return None
        domain = link_parts[site_id]

        if link_parts[site_id + 1] == "images":
            post_number = link_parts[site_id + 2]
        else:
            post_number = link_parts[site_id + 1]

        if not post_number.isdigit():
            print("Couldn't get image from url (post number is not a number): " + link)
            print()
            return None

        try:
            response = requests.get(
                "https://" + domain + "/api/v1/json/images/" + post_number, headers=headers)
            if response.status_code == 200:
                result = json.loads(response.text)
                return self._handle_image(result['image'], domain, allow_nsfw, spoil_nsfw)
            else:
                print("Couldn't get image from url (code=" +
                      str(response.status_code) + "): " + link)
                print()
                return None
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            traceback.print_exception(type(e), e, e.__traceback__)
            print("Couldn't get image from url: " + link)
            print()
            return None

    def _handle_image(self, booru_image, domain, allow_nsfw: bool = True, spoil_nsfw: bool = True) -> PostData | None:
        if not allow_nsfw and any(tag in booru_image['tags'] for tag in ["explicit", "grimdark", "grotesque", "questionable"]):
            return PostData(
                site="booru",
                post_type="text",
                post_id=booru_image['id'],
                text=(f"The requested image ({booru_image['id']}) is NSFW. "
                      "If you want to download it use >>? or >>!.\n\n"
                      ">>? will send the image with a spoiler.\n"
                      ">>! will send the image directly."),
            )

        post_data = PostData(
            site="booru",
            post_type="media",
            post_id=booru_image['id'],
            text=booru_image['description'],
            url="https://" + domain + "/" + str(booru_image['id']),
        )

        author = self._check_if_author_known(booru_image['tags'])
        if author:
            post_data.author = author

        match booru_image['format']:
            case "jpg" | "jpeg" | "png" | "svg":
                # to be changed when booru api handles svg better
                # (currently only low quality png is returned)
                # height + width > 8000 is safe margin because tg api has a limit of 10k
                # but some images under 10k where rejected
                if booru_image['height'] + booru_image['width'] > 8000:
                    post_data.media = [
                        [booru_image['representations']['large'], "photo"]]
                else:
                    post_data.media = [
                        [booru_image['representations']['full'], "photo"]]
            case "gif":
                post_data.media = [
                    [booru_image['representations']['full'], "gif"]]
            case "webm":
                self._handle_video(booru_image, post_data)
            case _:
                post_data.post_type = "text"
                post_data.text = "Unknown image format: " + \
                    booru_image['format'] + "\n" + post_data.text

        post_data.spoiler = booru_image['spoilered'] if spoil_nsfw else False

        return post_data

    def _check_if_author_known(self, tags):
        list_of_authors = []
        for tag in tags:
            if tag.startswith("artist:"):
                list_of_authors.append(tag[7:])
        if not list_of_authors:
            return None
        return ', '.join(list_of_authors)

    def _handle_video(self, booru_image, post_data: PostData) -> None:
        if self.CONVERT_WEBM_VIDEO:
            webm_filename = file_downloader.download_video(url=booru_image['representations']['full'],
                                                           site="booru",
                                                           id=str(booru_image['id']))

            converted_filename = file_converter.convert_webm_to_mp4(
                webm_filename)

            if converted_filename:
                post_data.media = [[converted_filename, "video_file"]]
            else:
                print("Couldn't convert webm to mp4: " + webm_filename)
                post_data.media = [
                    [booru_image['representations']['full'], "video"]]
        else:
            post_data.media = [
                [booru_image['representations']['full'], "video"]]
